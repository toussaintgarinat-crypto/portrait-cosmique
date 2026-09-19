const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');
function load(language) {
 const context = {LANGUE:language, document:{getElementById:()=>({checked:false,addEventListener(){}})}};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync('static/interface-support.js','utf8'),context);
 return context;
}
test('symbolic values use selected language without altering proper names',()=>{
 const c=load('en');
 for(const [fr,en] of [['Bélier','Aries'],['Chèvre','Goat'],['Saule','Willow'],['Saphir','Sapphire'],['Soleil','Sun'],['Noeud Nord','North Node']]) assert.equal(c.traduireValeur(fr),en);
 assert.equal(c.traduireValeur('Imix'),'Imix');
 c.LANGUE='fr'; assert.equal(c.traduireValeur('Bélier'),'Bélier');
});
test('birth timezone error stays English even when server detail is French', async()=>{
 const elements={};
 const document={getElementById(id){return elements[id] ||= {value:({latitude:'43',longitude:'2',date_naissance:'1990-09-05',heure_naissance:'11:05'})[id]||'',checked:false,addEventListener(){},replaceChildren(){}};}};
 const context={LANGUE:'en',document,window:{},fetch:async()=>({ok:false,json:async()=>({detail:'Coordonnées incorrectes.'})})};
 vm.createContext(context);vm.runInContext(fs.readFileSync('static/fuseau-auto.js','utf8'),context);
 await context.actualiserFuseau();
 assert.match(elements['fuseau-info'].textContent,/Unable to calculate time zone/);
 assert.doesNotMatch(elements['fuseau-info'].textContent,/Coordonnées/);
});
