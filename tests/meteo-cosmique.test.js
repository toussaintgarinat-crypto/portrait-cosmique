const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

function element(tag) {
  return {tag, open:false, querySelectorAll(selector) { return this.children.flatMap(n => [...(n.tag===selector?[n]:[]), ...(n.querySelectorAll?.(selector)||[])]); }, hidden:false, disabled:false, textContent:'', value:'', children:[],
    addEventListener() {}, append(...nodes) { this.children.push(...nodes); },
    appendChild(node) { this.children.push(node); return node; }, replaceChildren(...nodes) { this.children = nodes; }};
}
function charger() {
  const elements = Object.fromEntries(['meteo-generer','meteo-gps','meteo-ville-chercher','meteo-statut','meteo-resultat','meteo-ville-candidat','meteo-lieu-actif','meteo-lieu-reset','meteo-lieu','meteo-ville','meteo-lieu-ouvrir','onglet-horoscope','form-fiche'].map(id => [id, element()]));
  elements['onglet-horoscope'].hidden = true;
  const ctx = {window:{}, LANGUE:'fr', DERNIER_RESULTAT:null, AbortController, Date, JSON, Number, Object, String, Array, Error,
    Intl, setTimeout, clearTimeout, setInterval() {}, navigator:{},
    document:{visibilityState:'visible', getElementById:id => elements[id], addEventListener() {}, createElement:tag => element(tag)},
    profilHoroscope:() => ({date:'2026-09-13'}), dateLocaleHoroscope:() => '2026-09-13', lireChampsForm:() => ({utc_fold:'0', latitude:'1.2', longitude:'3.4'})};
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('static/meteo-cosmique.js', 'utf8'), ctx);
  return {ctx, elements};
}

test('formats a timestamp without incompatible Intl options', () => {
  const {ctx} = charger();
  assert.doesNotThrow(() => ctx.meteoDate('2026-09-13T12:00:00Z'));
});

test('normalises a form Fiche for Pydantic and resolved civil time', () => {
  const {ctx} = charger();
  const fiche = ctx.normaliserFicheMeteo({utc_fold:'0', latitude:'1.2', longitude:'3.4', utc_offset:'2'});
  assert.equal(fiche.utc_fold, 0);
  assert.equal(fiche.latitude, 1.2);
  assert.equal(fiche.longitude, 3.4);
  assert.equal(fiche.utc_offset, 2);
  assert.equal(fiche.utc_auto, true);
});

test('invalid profile does not leave a weather request or controls locked', async () => {
  const {ctx, elements} = charger();
  ctx.profilHoroscope = () => { throw new Error('profil invalide'); };
  ctx.etatMeteoCosmique().requete = new AbortController();
  elements['meteo-generer'].disabled = true;
  await ctx.chargerMeteoCosmique();
  assert.equal(ctx.etatMeteoCosmique().requete, null);
  assert.equal(elements['meteo-generer'].disabled, false);
});

test('late GPS callback cannot restore location after disabling it', async () => {
  const {ctx} = charger(); let success;
  ctx.navigator.geolocation = {getCurrentPosition:ok => { success=ok; }};
  ctx.chargerMeteoCosmique = () => {};
  ctx.demanderPositionMeteo();
  ctx.retirerLieuMeteo();
  success({coords:{latitude:48.85,longitude:2.35}});
  assert.equal(ctx.etatMeteoCosmique().localisation,null);
});

test('late weather response cannot render after profile invalidation', async () => {
  const {ctx, elements} = charger(); let release;
  ctx.fetch = () => new Promise(resolve => {release=resolve;});
  const request = ctx.chargerMeteoCosmique();
  ctx.reinitialiserMeteoCosmique();
  release({ok:true,json:async()=>({lecture:'OLD PROFILE',tendances:[],limites:[]})});
  await request;
  assert.equal(elements['meteo-resultat'].hidden,true);
  assert.equal(elements['meteo-resultat'].children.length,0);
  assert.equal(elements['meteo-generer'].disabled,false);
});

test('minute refresh does not interfere with a pending location choice', () => {
  const {ctx,elements} = charger(); let calls=0;
  ctx.chargerMeteoCosmique = () => {calls++;};
  elements['onglet-horoscope'].hidden=false;
  Object.assign(ctx.etatMeteoCosmique(),{generee:true,gpsEnCours:true});
  ctx.rafraichirMeteoSiNecessaire();
  assert.equal(calls,0);
  Object.assign(ctx.etatMeteoCosmique(),{gpsEnCours:false,geoRequete:{}});
  ctx.rafraichirMeteoSiNecessaire();
  assert.equal(calls,0);
});

test('failed refresh keeps the last valid reading and reports its timestamp', async () => {
  const {ctx,elements} = charger();
  Object.assign(ctx.etatMeteoCosmique(), {generee:true,jour:ctx.meteoJourLocal(),fuseau:ctx.meteoFuseau(),dernierInstant:'2026-09-13T12:00:00Z'});
  elements['meteo-resultat'].children=['valid reading']; elements['meteo-resultat'].hidden=false;
  ctx.fetch=async()=>{throw new Error('network unavailable');};
  await ctx.chargerMeteoCosmique();
  assert.equal(elements['meteo-resultat'].children[0],'valid reading');
  assert.equal(elements['meteo-resultat'].hidden,false);
  assert.match(elements['meteo-statut'].textContent,/Dernier calcul conservé/);
  assert.equal(elements['meteo-generer'].disabled,false);
});

 test('hourly advice is visible immediately and keeps the user choice on refresh', () => {
  const {ctx,elements} = charger();
  const data={natal_complet:true,date_locale:'2026-09-13',fuseau:'Europe/Paris',instant_utc:'2026-09-13T12:00:00Z',fenetres:[{debut:'2026-09-13T10:00:00Z',fin:'2026-09-13T14:00:00Z',conseil:'Prends une pause.'}]};
  ctx.meteoRendre(data);
  let windows=elements['meteo-resultat'].querySelectorAll('details')[0];
  assert.equal(windows.open,true);
  windows.open=false;
  ctx.meteoRendre(data);
  assert.equal(elements['meteo-resultat'].querySelectorAll('details')[0].open,false);
});
