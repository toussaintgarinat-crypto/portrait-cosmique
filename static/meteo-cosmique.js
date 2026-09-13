// Météo cosmique : transits personnels, avec localisation volontaire et éphémère.
function etatMeteoCosmique() {
  return window.__meteoCosmiqueEtat ||= {
    version: 0, geoVersion: 0, gpsVersion: 0, requete: null, geoRequete: null,
    gpsEnCours: false, localisation: null, generee: false, jour: null, fuseau: null, candidat: null
  };
}
function meteoTexte(fr, en) { return LANGUE === 'en' ? en : fr; }
function meteoEl(id) { return document.getElementById(id); }
function meteoFuseau() {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; }
  catch (_) { return 'UTC'; }
}
function meteoJourLocal() {
  const f = new Intl.DateTimeFormat('en-CA', {timeZone: meteoFuseau(), year:'numeric', month:'2-digit', day:'2-digit'});
  const p = Object.fromEntries(f.formatToParts(new Date()).filter(x => x.type !== 'literal').map(x => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
function meteoTexteSecurise(value) { return typeof value === 'string' ? value : ''; }
function meteoBoutons() {
  const etat = etatMeteoCosmique(); const occupe = !!etat.requete || etat.gpsEnCours;
  ['meteo-generer', 'meteo-gps', 'meteo-ville-chercher'].forEach(id => { const b = meteoEl(id); if (b) b.disabled = occupe; });
}
function meteoStatut(message) { meteoEl('meteo-statut').textContent = message || ''; }
function meteoDate(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return meteoTexteSecurise(value);
  return new Intl.DateTimeFormat(LANGUE === 'en' ? 'en-GB' : 'fr-FR', {
    year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', timeZone:meteoFuseau(), timeZoneName:'short'
  }).format(d);
}
function meteoAppendText(parent, tag, value, className) {
  const node = document.createElement(tag); if (className) node.className = className;
  node.textContent = meteoTexteSecurise(value); parent.append(node); return node;
}
function meteoListe(parent, items) {
  const valeurs = Array.isArray(items) ? items.filter(x => typeof x === 'string' && x.trim()) : [];
  if (!valeurs.length) return;
  const list = document.createElement('ul'); valeurs.forEach(x => meteoAppendText(list, 'li', x)); parent.append(list);
}
function meteoRendre(data) {
  const result = meteoEl('meteo-resultat');
  const ouverts = Array.from(result.querySelectorAll('details'), d=>d.open);
  result.replaceChildren(); result.hidden = false;
  if (!data.natal_complet) meteoAppendText(result, 'p', meteoTexte('Lecture partielle : heure de naissance inconnue, Soleil natal approximé à midi.', 'Partial reading: birth time unknown, natal Sun estimated at noon.'), 'meteo-limites');
  if (data.lecture) meteoAppendText(result, 'p', data.lecture, 'meteo-lecture');

  const tendances = Array.isArray(data.tendances) ? data.tendances.slice(0, 3) : [];
  if (tendances.length) {
    const bloc = document.createElement('div'); bloc.className = 'meteo-trends';
    tendances.forEach(t => {
      const card = document.createElement('article'); card.className = 'meteo-tendance';
      meteoAppendText(card, 'h4', t?.nom || meteoTexte('Tendance', 'Trend'));
      const niveau = [t?.niveau, t?.tonalite].filter(x => typeof x === 'string' && x).join(' · ');
      if (niveau) meteoAppendText(card, 'p', niveau);
      const repere = document.createElement('div'); repere.className = 'meteo-repere';
      repere.setAttribute('aria-hidden', 'true');
      const intensite = ['discret','modéré','marqué'].indexOf(t.niveau)+1;
      for (let i=0; i<3; i++) { const segment=document.createElement('span'); segment.className=i<intensite?'actif':''; repere.append(segment); }
      card.append(repere);
      const detail = document.createElement('details'); detail.className='meteo-facteurs';
      meteoAppendText(detail, 'summary', meteoTexte('Comprendre cette tendance', 'Understand this trend'));
      if (t?.explication) meteoAppendText(detail, 'p', t.explication);
      const facteurs = Array.isArray(t?.facteurs) ? t.facteurs.map(f => {
        if (typeof f === 'string') return f;
        return `${[f?.mobile, f?.aspect, f?.natal].filter(Boolean).join(' ')} natal · ${Number(f.orb).toFixed(2)}° d’orbe`;
      }) : [];
      meteoListe(detail, facteurs);
      card.append(detail);
      bloc.append(card);
    });
    result.append(bloc);
  }

  if (data.local) {
    const local = document.createElement('details'); local.className = 'meteo-detail';
    const summary = document.createElement('summary'); summary.textContent = meteoTexte('Ici et maintenant', 'Here and now'); local.append(summary);
    const angles = [
      data.local.ascendant && `Ascendant : ${data.local.ascendant.signe || ''}`,
      data.local.milieu_du_ciel && `Milieu du Ciel : ${data.local.milieu_du_ciel.signe || ''}`
    ].filter(Boolean).join(' · ');
    if (angles) meteoAppendText(local, 'p', angles);
    const maisons = Array.isArray(data.local.maisons) ? data.local.maisons.map(m => `${meteoTexte('Maison', 'House')} ${m.maison} : ${m.signe || ''}`) : [];
    meteoListe(local, maisons);
    const precision = [meteoTexte('Maisons locales en signes entiers', 'Local whole-sign houses'), data.local.fuseau].filter(Boolean).join(' · ');
    if (precision) meteoAppendText(local, 'p', precision);
    result.append(local);
  }

  const fenetres = Array.isArray(data.fenetres) ? data.fenetres : [];
  if (fenetres.length) {
    const windows = document.createElement('details'); windows.className = 'meteo-detail';
    const summary = document.createElement('summary'); summary.textContent = meteoTexte('Fenêtres de la journée', 'Today’s windows'); windows.append(summary);
    const list = document.createElement('ul');
    meteoAppendText(windows, 'p', `${data.date_locale} · ${data.fuseau} · ${meteoTexte('Horaires dans le fuseau de ton navigateur.', 'Times in your browser time zone.')}`);
    const horloge = new Intl.DateTimeFormat(LANGUE==='en'?'en-GB':'fr-FR', {hour:'2-digit', minute:'2-digit',timeZone:data.fuseau,timeZoneName:'short'});
    fenetres.forEach(f => {
      const ligne = document.createElement('li');
      const debut = new Date(f.debut), fin = new Date(f.fin);
      const actuel = new Date(data.instant_utc)>=debut && new Date(data.instant_utc)<fin;
      if (actuel) ligne.className='meteo-fenetre-actuelle';
      meteoAppendText(ligne, 'strong', `${horloge.format(debut)} — ${horloge.format(fin)}${actuel?meteoTexte(' · Maintenant',' · Now'):''}`);
      meteoAppendText(ligne, 'p', `${f.domaine} · ${meteoTexte('Ascendant','Rising sign')} ${f.ascendant} · ${meteoTexte('Soleil en maison locale','Sun in local house')} ${f.maison_solaire}`);
      meteoAppendText(ligne, 'p', f.conseil);
      list.append(ligne);
    });
    windows.append(list); result.append(windows);
  }
  if (Array.isArray(data.limites) && data.limites.length) {
    meteoAppendText(result, 'p', meteoTexte('Lecture symbolique · éphémérides approchées · tendances non mesurées.', 'Symbolic reading · approximate ephemerides · not measured traits.'), 'meteo-limites');
    const limits = document.createElement('details'); limits.className = 'meteo-detail meteo-limites';
    meteoAppendText(limits, 'summary', meteoTexte('Méthode et limites du calcul', 'Method and limitations'));
    meteoListe(limits, data.limites); result.append(limits);
  }
  result.querySelectorAll('details').forEach((d,i)=>{ d.open=ouverts[i] || false; });
}
function viderResultatMeteo() {
  meteoEl('meteo-resultat').replaceChildren(); meteoEl('meteo-resultat').hidden = true;
}
function invaliderMeteo() {
  const etat = etatMeteoCosmique(); etat.version++; etat.requete?.abort(); etat.requete = null;
  etat.generee = false; etat.jour = etat.fuseau = null; viderResultatMeteo(); meteoBoutons();
}
function invaliderCandidatMeteo() {
  const etat = etatMeteoCosmique(); etat.geoVersion++; etat.geoRequete?.abort(); etat.geoRequete = null; etat.candidat = null;
  meteoEl('meteo-ville-candidat').replaceChildren(); meteoEl('meteo-ville-candidat').hidden = true;
}
function annulerGPSMeteo() { const etat = etatMeteoCosmique(); etat.gpsVersion++; etat.gpsEnCours = false; meteoBoutons(); }
function reinitialiserMeteoCosmique() {
  invaliderMeteo(); invaliderCandidatMeteo(); annulerGPSMeteo(); meteoStatut('');
}
function nombreMeteo(value) { if (value === '' || value == null) return null; const n = Number(value); return Number.isFinite(n) ? n : null; }
function normaliserFicheMeteo(fiche) {
  const normalisee = {...fiche, utc_auto:true};
  ['latitude', 'longitude', 'utc_offset'].forEach(cle => { normalisee[cle] = nombreMeteo(normalisee[cle]); });
  normalisee.utc_fold = normalisee.utc_fold === '' || normalisee.utc_fold == null ? null : nombreMeteo(normalisee.utc_fold);
  if (normalisee.heure_inconnue || !normalisee.heure_naissance) normalisee.heure_naissance = null;
  return normalisee;
}
async function chargerMeteoCosmique() {
  const etat = etatMeteoCosmique(); const version = ++etat.version; etat.requete?.abort(); etat.requete = null;
  let profil;
  try { profil = profilHoroscope(); }
  catch (e) { meteoBoutons(); meteoStatut(e.message); return; }
  const conserve = etat.generee && etat.jour===meteoJourLocal() && etat.fuseau===meteoFuseau();
  if (!conserve) { etat.generee=false; viderResultatMeteo(); }
  const controller = new AbortController(); etat.requete = controller;
  meteoBoutons(); meteoStatut(meteoTexte('Calcul des transits en cours…', 'Calculating transits…'));
  const timeout = setTimeout(() => controller.abort(), 30000);
  const fuseau = meteoFuseau(); const jour = meteoJourLocal(); const resultat = DERNIER_RESULTAT; const localisation = etat.localisation;
  try {
    const response = await fetch('/meteo-cosmique', {method:'POST', headers:{'Content-Type':'application/json'}, signal:controller.signal,
      body:JSON.stringify({fiche:normaliserFicheMeteo(lireChampsForm()), fuseau, localisation:localisation?{latitude:localisation.latitude,longitude:localisation.longitude}:null})});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : meteoTexte('La météo cosmique est indisponible.', 'Cosmic weather is unavailable.'));
    if (version !== etat.version || resultat !== DERNIER_RESULTAT || profil.date !== dateLocaleHoroscope() || fuseau !== meteoFuseau() || localisation !== etat.localisation) return;
    meteoRendre(data); etat.dernierInstant = data.instant_utc; etat.generee = true; etat.jour = jour; etat.fuseau = fuseau;
    meteoStatut(`${meteoTexte('Mise à jour', 'Updated')} : ${meteoDate(data.instant_utc)} · ${data.date_locale || jour} · ${fuseau}`);
  } catch (e) {
    if (version !== etat.version) return;
    meteoStatut((e.name === 'AbortError' ? meteoTexte('Le délai est dépassé. Réessaie.', 'The request timed out. Try again.') : e.message) + (conserve ? meteoTexte(' Dernier calcul conservé : ', ' Last calculation retained: ') + meteoDate(etat.dernierInstant) : ''));
  } finally { clearTimeout(timeout); if (version === etat.version) { etat.requete = null; meteoBoutons(); } }
}
function ouvrirLieuMeteo() { meteoEl('meteo-lieu').hidden = !meteoEl('meteo-lieu').hidden; }
function rendreLieuActif() {
  const etat = etatMeteoCosmique(); const target = meteoEl('meteo-lieu-actif');
  meteoEl('meteo-lieu-ouvrir').textContent = etat.localisation ? meteoTexte('Changer de lieu', 'Change location') : meteoTexte('Activer la météo cosmique locale', 'Enable local cosmic weather');
  meteoEl('meteo-generer').textContent = etat.localisation ? meteoTexte('Analyser ici & maintenant', 'Analyse here & now') : meteoTexte('Actualiser mes transits', 'Refresh my transits');
  if (!etat.localisation) { target.hidden = true; target.textContent = ''; meteoEl('meteo-lieu-reset').hidden = true; return; }
  const {label, latitude, longitude, date} = etat.localisation;
  target.textContent = `${meteoTexte('Lieu de cette session', 'Session location')} : ${label || `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`} · ${meteoDate(date)}`;
  target.hidden = false; meteoEl('meteo-lieu-reset').hidden = false;
}
function appliquerLieuMeteo(candidate) {
  if (!candidate || !Number.isFinite(candidate.latitude) || !Number.isFinite(candidate.longitude)) return;
  const etat = etatMeteoCosmique(); invaliderMeteo(); invaliderCandidatMeteo(); annulerGPSMeteo();
  etat.localisation = {...candidate, date:new Date().toISOString()}; rendreLieuActif();
  chargerMeteoCosmique();
}
async function chercherVilleMeteo() {
  const ville = meteoEl('meteo-ville').value.trim(); if (!ville) return;
  const etat = etatMeteoCosmique(); invaliderCandidatMeteo(); annulerGPSMeteo(); const version = ++etat.geoVersion;
  const controller = new AbortController(); etat.geoRequete = controller;
  meteoStatut(meteoTexte('Recherche de la ville…', 'Searching for city…'));
  let timeoutAtteint = false;
  const timeout = setTimeout(() => { timeoutAtteint = true; controller.abort(); }, 10000);
  try {
    const response = await fetch('/geo?ville=' + encodeURIComponent(ville), {signal:controller.signal});
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !Number.isFinite(data.latitude) || !Number.isFinite(data.longitude)) throw new Error(meteoTexte('Ville introuvable.', 'City not found.'));
    if (version !== etat.geoVersion || etat.geoRequete !== controller || ville !== meteoEl('meteo-ville').value.trim()) return;
    etat.candidat = {label:data.ville || ville, latitude:data.latitude, longitude:data.longitude};
    const candidate = meteoEl('meteo-ville-candidat'); candidate.replaceChildren();
    meteoAppendText(candidate, 'span', `${etat.candidat.label} (${data.latitude.toFixed(3)}, ${data.longitude.toFixed(3)})`);
    const choose = document.createElement('button'); choose.type = 'button'; choose.className = 'btn ghost'; choose.textContent = meteoTexte('Utiliser cette ville', 'Use this city');
    choose.addEventListener('click', () => appliquerLieuMeteo(etat.candidat)); candidate.append(choose); candidate.hidden = false; meteoStatut('');
  } catch (e) {
    if (version !== etat.geoVersion || etat.geoRequete !== controller) return;
    if (timeoutAtteint) meteoStatut(meteoTexte('La recherche de ville a expiré. Réessaie.', 'City search timed out. Try again.'));
    else if (e.name !== 'AbortError') meteoStatut(e.message);
  }
  finally { clearTimeout(timeout); if (etat.geoRequete === controller) etat.geoRequete = null; }
}
function demanderPositionMeteo() {
  if (!navigator.geolocation) { meteoStatut(meteoTexte('La géolocalisation est indisponible dans ce navigateur.', 'Geolocation is unavailable in this browser.')); return; }
  const etat = etatMeteoCosmique(); invaliderCandidatMeteo(); const version = ++etat.gpsVersion; etat.gpsEnCours = true; meteoBoutons();
  meteoStatut(meteoTexte('Demande de position au navigateur…', 'Requesting browser location…'));
  navigator.geolocation.getCurrentPosition(pos => {
    if (version !== etat.gpsVersion) return;
    etat.gpsEnCours = false; meteoBoutons(); appliquerLieuMeteo({label:meteoTexte('Position du navigateur', 'Browser location'), latitude:pos.coords.latitude, longitude:pos.coords.longitude});
  }, err => {
    if (version !== etat.gpsVersion) return;
    etat.gpsEnCours = false; meteoBoutons(); meteoStatut(err.code === err.PERMISSION_DENIED ? meteoTexte('Position non autorisée. La météo de base reste disponible.', 'Location was not allowed. Base weather remains available.') : meteoTexte('Position indisponible. La météo de base reste disponible.', 'Location unavailable. Base weather remains available.'));
  }, {enableHighAccuracy:false, timeout:10000, maximumAge:0});
}
function retirerLieuMeteo() { const etat = etatMeteoCosmique(); invaliderMeteo(); invaliderCandidatMeteo(); annulerGPSMeteo(); etat.localisation = null; rendreLieuActif(); chargerMeteoCosmique(); }
function rafraichirMeteoSiNecessaire() {
  const etat = etatMeteoCosmique();
  if (!etat.generee || etat.requete || etat.gpsEnCours || etat.geoRequete || document.visibilityState !== 'visible' || meteoEl('onglet-horoscope').hidden) return;
  // La même cadence couvre le passage de minuit, un changement de fuseau et DST.
  chargerMeteoCosmique();
}
meteoEl('meteo-generer').addEventListener('click', chargerMeteoCosmique);
meteoEl('meteo-lieu-ouvrir').addEventListener('click', ouvrirLieuMeteo);
meteoEl('meteo-gps').addEventListener('click', demanderPositionMeteo);
meteoEl('meteo-lieu-reset').addEventListener('click', retirerLieuMeteo);
meteoEl('meteo-ville-chercher').addEventListener('click', chercherVilleMeteo);
meteoEl('meteo-ville').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); chercherVilleMeteo(); } });
meteoEl('meteo-ville').addEventListener('input', invaliderCandidatMeteo);
document.addEventListener('visibilitychange', rafraichirMeteoSiNecessaire);
setInterval(rafraichirMeteoSiNecessaire, 60000);
