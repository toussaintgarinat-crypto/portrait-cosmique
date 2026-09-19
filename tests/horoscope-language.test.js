const assert=require('node:assert/strict');
const fs=require('node:fs');
const test=require('node:test');
const vm=require('node:vm');
function setup(language) {
  const elements={}; let spoken;
  const document={getElementById:id=>elements[id] ||= {textContent:'',disabled:false,value:'',style:{display:'none'},setAttribute(){},addEventListener(){}},querySelectorAll:()=>[]};
  const ctx={LANGUE:language,I18N:{fr:{},en:{}},document,Date,JSON,AbortController,setTimeout,clearTimeout,DERNIER_RESULTAT:{donnees_synthetiques:{astrologie:{soleil:'Vierge'}}},lireChampsForm:()=>({}),addEventListener(){},SpeechSynthesisUtterance:function(t){this.text=t;},speechSynthesis:{cancel(){},getVoices:()=>[{lang:'fr-FR'},{lang:'en-GB'}],speak:u=>spoken=u}};
  ctx.window=ctx; vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/horoscope.js','utf8'),ctx);
  ctx.etatHoroscope().profilSignature='{}';
  return {ctx,elements,spoken:()=>spoken};
}
for (const language of ['fr','en']) {
 test(`API ${language} sends explicit language without accessing AI configuration`,async()=>{
  const {ctx,elements}=setup(language);let payload;
  ctx.configurationHoroscopeIA=()=>{throw new Error('API should not read key');};
  ctx.fetch=async(url,options)=>{payload=JSON.parse(options.body);return {ok:true,json:async()=>({texte:language==='fr'?'Une pause.':'A break.',langue:language,date:ctx.dateLocaleHoroscope()})};};
  await ctx.chargerHoroscopeAPI();
  assert.equal(payload?.langue,language);
  assert.equal(payload.llm,null);
  assert.equal(elements['horoscope-texte'].lang,language);
 });
 test(`audio ${language} chooses matching voice`,()=>{
  const {ctx,elements,spoken}=setup(language);
  ctx.etatHoroscope().date=ctx.dateLocaleHoroscope();
  elements['horoscope-texte']={textContent:'Test',lang:language};
  ctx.lireHoroscopeAudio();
  assert.equal(spoken().lang.startsWith(language),true);
  assert.equal(spoken().voice.lang.startsWith(language),true);
 });
}
test('late response from previous language is discarded',async()=>{
 const {ctx,elements}=setup('fr');let resolve;
 ctx.configurationHoroscopeIA=()=>null;
 ctx.fetch=()=>new Promise(r=>resolve=r);
 const pending=ctx.chargerHoroscopeAPI();ctx.LANGUE='en';
 resolve({ok:true,json:async()=>({texte:'Ancienne lecture',langue:'fr',date:ctx.dateLocaleHoroscope()})});
 await pending;
 assert.equal(elements['horoscope-texte'].textContent,'');
});
