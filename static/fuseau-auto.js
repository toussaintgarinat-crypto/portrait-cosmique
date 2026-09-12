// Resolve civil birth time against the historical rules of its geographical zone.
function etatFuseau() { return window.__fuseauEtat ||= {sequence: 0}; }
function texteFuseau(fr, en) { return LANGUE === 'en' ? en : fr; }
function offsetLisible(offset) {
  const minutes = Math.round(Math.abs(offset) * 60);
  return `UTC${offset < 0 ? '−' : '+'}${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}
async function actualiserFuseau(foldRestaure) {
  const champ = id => document.getElementById(id);
  const etat = etatFuseau();
  const seq = ++etat.sequence;
  const body = {
    latitude: champ('latitude').value === '' ? null : Number(champ('latitude').value),
    longitude: champ('longitude').value === '' ? null : Number(champ('longitude').value),
    date_naissance: champ('date_naissance').value,
    heure_naissance: champ('heure_inconnue').checked ? null : champ('heure_naissance').value || null,
  };
  const signature = JSON.stringify(body);
  const choix = champ('utc_fold');
  const fold = foldRestaure ?? (etat.signature === signature ? choix.value : '');
  champ('utc_offset').value = '';
  choix.hidden = champ('utc-fold-label').hidden = true;
  choix.replaceChildren();
  etat.signature = signature;
  const info = champ('fuseau-info');
  if (!body.date_naissance || body.latitude === null || body.longitude === null) {
    info.textContent = body.heure_naissance
      ? texteFuseau('Localise la ville de naissance pour calculer automatiquement le fuseau.', 'Locate the birthplace to calculate its time zone automatically.')
      : texteFuseau('Le fuseau sera calculé automatiquement avec le lieu, la date et l’heure de naissance.', 'The time zone is calculated automatically from the birthplace, date and time.');
    return !body.heure_naissance;
  }
  info.textContent = texteFuseau('Calcul du fuseau de naissance…', 'Calculating birth time zone…');
  try {
    const response = await fetch('/fuseau', {method:'POST', headers:{'Content-Type':'application/json'}, body:signature});
    const d = await response.json();
    if (seq !== etat.sequence) return false;
    if (!response.ok) throw new Error(typeof d.detail === 'string' ? d.detail : texteFuseau('Fuseau indisponible.', 'Time zone unavailable.'));
    if (d.statut === 'heure_ambigue') {
      choix.append(new Option(texteFuseau('Choisir la première ou la seconde occurrence', 'Choose the first or second occurrence'), ''));
      d.choix.forEach(c => choix.append(new Option(`${c.fold === 0 ? texteFuseau('Première', 'First') : texteFuseau('Seconde', 'Second')} · ${c.abbreviation} · ${offsetLisible(c.utc_offset)}`, String(c.fold))));
      choix.value = fold == null ? '' : String(fold);
      choix.hidden = champ('utc-fold-label').hidden = false;
      const selected = d.choix.find(c => String(c.fold) === choix.value);
      info.textContent = `${d.fuseau} · ${texteFuseau('Cette heure a eu lieu deux fois lors du changement d’heure. Précise laquelle.', 'This clock time occurred twice during the clock change. Choose its occurrence.')}`;
      if (selected) champ('utc_offset').value = selected.utc_offset;
      return !!selected;
    }
    if (d.statut === 'heure_inexistante') {
      info.textContent = `${d.fuseau} · ${texteFuseau('Cette heure n’existe pas à cette date, en raison du changement d’heure. Vérifie l’heure de naissance.', 'This clock time does not exist on that date due to the clock change. Check the birth time.')}`;
      return false;
    }
    if (d.utc_offset != null) champ('utc_offset').value = d.utc_offset;
    info.textContent = d.utc_offset == null ? d.fuseau : `${d.fuseau} · ${offsetLisible(d.utc_offset)} · ${texteFuseau('calculé pour la date de naissance', 'calculated for the birth date')}`;
    return true;
  } catch (e) {
    if (seq !== etat.sequence) return false;
    info.textContent = texteFuseau('Calcul du fuseau impossible. ', 'Unable to calculate time zone. ') + e.message;
    return !body.heure_naissance;
  }
}
async function localiser() {
  const ville = document.getElementById('ville').value.trim();
  if (!ville) return false;
  const etat = etatFuseau();
  if (etat.ville === ville && etat.localisation) return etat.localisation;
  etat.ville = ville;
  const promise = (async () => {
    try {
      const r = await fetch('/geo?ville=' + encodeURIComponent(ville));
      if (!r.ok) throw new Error();
      const d = await r.json();
      if (ville !== document.getElementById('ville').value.trim()) return false;
      document.getElementById('latitude').value = d.latitude;
      document.getElementById('longitude').value = d.longitude;
      document.getElementById('coords-info').textContent = `${d.ville} (${d.latitude.toFixed(2)}, ${d.longitude.toFixed(2)})`;
      await actualiserFuseau();
      return true;
    } catch (_) {
      if (ville === document.getElementById('ville').value.trim()) document.getElementById('coords-info').textContent = texteFuseau('Ville introuvable.', 'City not found.');
      return false;
    }
  })();
  etat.localisation = promise;
  try { return await promise; } finally { if (etat.localisation === promise) etat.localisation = null; }
}
['heure_inconnue', 'utc_fold'].forEach(id => {
  document.getElementById(id).addEventListener('change', () => { synchroniserHeure(); actualiserFuseau(); });
});
document.getElementById('ville').addEventListener('input', () => {
  document.getElementById('latitude').value = '';
  document.getElementById('longitude').value = '';
  document.getElementById('coords-info').textContent = '';
  actualiserFuseau();
});
document.getElementById('ville').addEventListener('change', () => localiser());

['date_naissance', 'heure_naissance'].forEach(id => {
  document.getElementById(id).addEventListener('input', () => actualiserFuseau());
});
