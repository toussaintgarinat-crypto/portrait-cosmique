const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

test('saved provider, key and model survive repeated page loads', () => {
  const config = {fournisseur:'custom',base_url:'https://example.test/v1',cle:'test-secret',modele:'test-model'};
  const storage = new Map([['config',JSON.stringify(config)]]);
  for (let i=0;i<2;i++) {
    const elements = {};
    const document = {getElementById(id) { return elements[id] ||= {value:id==='llm_fournisseur'?'openrouter':'',style:{display:id==='llm_modele_select'?'none':''},addEventListener(){}}; }};
    const context = {document, localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},LLM_STORAGE_KEY:'config',I18N:{fr:{}},LANGUE:'fr',setTimeout,clearTimeout};
    vm.createContext(context);
    const html=fs.readFileSync('static/index.html','utf8');
    vm.runInContext(html.slice(html.indexOf('const FOURNISSEURS ='),html.indexOf('// ── Multi-profils : peuplement')),context);
    assert.equal(elements.llm_cle.value,config.cle);
    assert.equal(elements.llm_modele.value,config.modele);
    assert.deepEqual(JSON.parse(storage.get('config')),config);
    vm.runInContext('effacerConfigLLM()',context);
    assert.equal(storage.has('config'),false);
    storage.set('config',JSON.stringify(config));
  }
});
