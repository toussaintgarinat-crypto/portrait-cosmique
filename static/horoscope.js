// Shared state is initialized lazily: restoring a saved profile happens before
// this injected script reaches its event bindings.
function etatHoroscope() {
  return window.__horoscopeEtat ||= {version: 0, requete: null, voix: null, date: null};
}
function hTexte(fr, en) { return LANGUE === 'en' ? en : fr; }
function dateLocaleHoroscope() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function audioHoroscopeDisponible() {
  return 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
}
function boutonsHoroscope(occupe) {
  document.querySelectorAll('[data-horoscope-generation]').forEach(b => { b.disabled = occupe; });
  document.getElementById('onglet-horoscope').setAttribute('aria-busy', String(occupe));
}
function arreterAudio() {
  const etat = etatHoroscope();
  etat.voix = null;
  if (audioHoroscopeDisponible()) window.speechSynthesis.cancel();
  document.getElementById('horoscope-arreter').disabled = true;
  document.getElementById('horoscope-ecouter').disabled = !audioHoroscopeDisponible() ||
    !document.getElementById('horoscope-texte').textContent.trim();
  document.getElementById('horoscope-audio-statut').textContent = '';
}
function reinitialiserHoroscope({conserverMeteo = false} = {}) {
  if (!conserverMeteo) window.reinitialiserMeteoCosmique?.();
  const etat = etatHoroscope();
  etat.version++;
  etat.requete?.abort();
  etat.requete = null;
  etat.date = null;
  arreterAudio();
  boutonsHoroscope(false);
  document.getElementById('horoscope-texte').textContent = '';
  document.getElementById('horoscope-statut').textContent = '';
  document.getElementById('horoscope-ecouter').disabled = true;
}
function profilHoroscope() {
  if (!DERNIER_RESULTAT) throw new Error(hTexte('Calcule d’abord ton portrait.', 'Calculate your portrait first.'));
  if (etatHoroscope().profilSignature !== JSON.stringify(lireChampsForm())) {
    throw new Error(hTexte('Le profil a changé. Recalcule ton portrait avant l’horoscope.', 'The profile changed. Recalculate your portrait before generating a horoscope.'));
  }
  const astro = DERNIER_RESULTAT.donnees_synthetiques?.astrologie || {};
  if (!astro.soleil) throw new Error(hTexte('Le signe solaire est indisponible.', 'The Sun sign is unavailable.'));
  return {date:dateLocaleHoroscope(), soleil:astro.soleil, ascendant:astro.ascendant || null, lune:astro.lune || null};
}
function configurationHoroscopeIA() {
  const fournisseur = document.getElementById('llm_fournisseur').value;
  const base_url = fournisseur === 'custom'
    ? document.getElementById('llm_base_url').value.trim()
    : FOURNISSEURS[fournisseur]?.base_url;
  const cle = document.getElementById('llm_cle').value.trim();
  const select = document.getElementById('llm_modele_select');
  const modele = select.style.display !== 'none' ? select.value : document.getElementById('llm_modele').value.trim();
  return cle ? {base_url, cle, modele} : null;
}
async function genererHoroscope(mode) {
  reinitialiserHoroscope({conserverMeteo:true});
  const etat = etatHoroscope();
  const version = etat.version;
  const resultat = DERNIER_RESULTAT;
  const controller = new AbortController();
  etat.requete = controller;
  const statut = document.getElementById('horoscope-statut');
  const timeout = setTimeout(() => controller.abort(), 70000);
  try {
    const profil = profilHoroscope();
    boutonsHoroscope(true);
    statut.textContent = hTexte('Génération en cours…', 'Generating…');
    const response = await fetch('/horoscope-du-jour', {
      method:'POST', headers:{'Content-Type':'application/json'}, signal:controller.signal,
      body:JSON.stringify({...profil, mode, llm:mode === 'ia' ? configurationHoroscopeIA() : null})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : hTexte('La génération a échoué.', 'Generation failed.'));
    if (typeof data.texte !== 'string' || !data.texte.trim()) throw new Error(hTexte('Le service a renvoyé un texte vide.', 'The service returned empty text.'));
    if (version !== etat.version || resultat !== DERNIER_RESULTAT) return;
    if (profil.date !== dateLocaleHoroscope()) throw new Error(hTexte('Le jour a changé. Relance la génération.', 'The day has changed. Generate a new reading.'));
    etat.date = profil.date;
    const lecture = document.getElementById('horoscope-texte');
    lecture.textContent = data.texte;
    lecture.lang = data.langue === 'en' ? 'en' : 'fr';
    statut.textContent = `${data.date || profil.date} · ${profil.soleil} · ${mode === 'ia' ? hTexte('IA personnalisée', 'Personalized AI') : hTexte('API · texte anglais', 'API · English text')}`;
    if (mode === 'api' && data.date !== profil.date) statut.textContent += hTexte(' · Date du fournisseur différente du jour local.', ' · Provider date differs from your local date.');
    document.getElementById('horoscope-ecouter').disabled = !audioHoroscopeDisponible();
    document.getElementById('horoscope-audio-statut').textContent = !audioHoroscopeDisponible()
      ? hTexte('La lecture audio est indisponible dans ce navigateur.', 'Speech is unavailable in this browser.')
      : mode === 'api' ? hTexte('La voix française ne traduit pas le texte anglais.', 'The French voice does not translate English text.') : '';
  } catch (e) {
    if (version !== etat.version) return;
    statut.textContent = e.name === 'AbortError'
      ? hTexte('Le délai est dépassé. Réessaie.', 'The request timed out. Try again.') : e.message;
  } finally {
    clearTimeout(timeout);
    if (version === etat.version) { etat.requete = null; boutonsHoroscope(false); }
  }
}
function chargerHoroscopeAPI() { return genererHoroscope('api'); }
function chargerHoroscopeIA() { return genererHoroscope('ia'); }
function lireHoroscopeAudio() {
  if (!audioHoroscopeDisponible()) return;
  const etat = etatHoroscope();
  if (etat.date !== dateLocaleHoroscope()) {
    reinitialiserHoroscope();
    document.getElementById('horoscope-statut').textContent = hTexte('Relance la génération pour aujourd’hui.', 'Generate a reading for today.');
    return;
  }
  const texte = document.getElementById('horoscope-texte').textContent.trim();
  if (!texte) return;
  arreterAudio();
  const utterance = new SpeechSynthesisUtterance(texte);
  utterance.lang = 'fr-FR';
  utterance.rate = 0.95;
  const voix = window.speechSynthesis.getVoices();
  const francaise = voix.find(v => v.lang === 'fr-FR') || voix.find(v => v.lang.toLowerCase().startsWith('fr'));
  if (francaise) utterance.voice = francaise;
  etat.voix = utterance;
  document.getElementById('horoscope-ecouter').disabled = true;
  document.getElementById('horoscope-arreter').disabled = false;
  const statut = document.getElementById('horoscope-audio-statut');
  statut.textContent = hTexte('Lecture en cours…', 'Reading…');
  const terminer = message => {
    if (etat.voix !== utterance) return;
    etat.voix = null;
    document.getElementById('horoscope-ecouter').disabled = false;
    document.getElementById('horoscope-arreter').disabled = true;
    statut.textContent = message;
  };
  utterance.onend = () => terminer('');
  utterance.onerror = () => terminer(hTexte('La lecture audio a été interrompue.', 'Speech was interrupted.'));
  try { window.speechSynthesis.speak(utterance); }
  catch (_) { terminer(hTexte('Lecture audio indisponible.', 'Speech unavailable.')); }
}
window.addEventListener('pagehide', arreterAudio);
// Result recalculation will provide the new profile; do not retain an old reading.
document.getElementById('form-fiche').addEventListener('input', reinitialiserHoroscope);
document.getElementById('form-fiche').addEventListener('change', reinitialiserHoroscope);
Object.assign(I18N.fr, {h_onglet:'Horoscope du jour', h_badge:'Une pause pour aujourd’hui',
  h_intro:'Une lecture symbolique : par signe solaire avec l’API, ou personnalisée avec ton Soleil, ta Lune et ton ascendant disponibles.',
  h_api:'⚡ API rapide · anglais', h_ia:'✨ IA personnalisée · français', h_ecouter:'🔊 Écouter', h_arreter:'⏹ Arrêter',
  h_note:'L’API est gratuite. L’IA utilise ta configuration existante et les éventuels frais de ton fournisseur. Ces deux lectures complémentaires n’utilisent pas les transits calculés ci-dessus.'});
Object.assign(I18N.en, {h_onglet:'Daily horoscope', h_badge:'A moment for today',
  h_intro:'A symbolic reading: by Sun sign through the API, or personalized with your available Sun, Moon and rising signs.',
  h_api:'⚡ Quick API · English', h_ia:'✨ Personalized AI · French', h_ecouter:'🔊 Listen', h_arreter:'⏹ Stop',
  h_note:'The API is free. AI uses your existing configuration and any provider charges. These two additional readings do not use the transits calculated above.'});
