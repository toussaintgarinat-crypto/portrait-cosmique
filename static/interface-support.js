function nomAspect(key) {
  return GLOSSAIRE_LABELS[_ASPECT_GLOSS[key]] || NOMS_ASPECTS_TR[key] || key;
}
// Form state and clean poster exports shared by the existing interface.
function echapperIdentite(value) {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function synchroniserHeure() {
  const inconnue = document.getElementById('heure_inconnue').checked;
  const heure = document.getElementById('heure_naissance');
  heure.disabled = inconnue;
  if (inconnue) heure.value = '';
  document.getElementById('utc_offset').required = false;
}
function synchroniserCarte() {
  const connue = !!(_THEME_CACHE && _THEME_CACHE.meta && _THEME_CACHE.meta.heure_connue);
  document.getElementById('theme-heure-inconnue').hidden = connue;
  document.getElementById('onglet-theme').classList.toggle('sans-heure',!connue);
  document.querySelectorAll('#onglet-theme .theme-layout, #onglet-theme .theme-options, #onglet-theme .fil-rouge').forEach(el => { el.style.display = connue ? '' : 'none'; });
  const ciel = document.querySelector('input[name="poster-type"][value="ciel"]');
  ciel.disabled = !connue;
  if (!connue && ciel.checked) document.querySelector('input[name="poster-type"][value="matrice"]').checked = true;
  document.getElementById('poster-densite-fieldset').style.display = ciel.checked ? '' : 'none';
}
function preparerSVGPoster(original, transparent = false) {
  const clone = original.cloneNode(true);
  const props = ['fill','stroke','stroke-width','stroke-opacity','fill-opacity','opacity','font-family','font-size','font-weight','letter-spacing','text-anchor','dominant-baseline','stroke-linecap','stroke-dasharray'];
  const originals = [original, ...original.querySelectorAll('*')];
  const copies = [clone, ...clone.querySelectorAll('*')];
  originals.forEach((node, i) => {
    const style = getComputedStyle(node);
    props.forEach(p => copies[i].style.setProperty(p, style.getPropertyValue(p)));
    for (const attr of [...copies[i].attributes]) {
      if (attr.name.startsWith('on') || attr.name.startsWith('data-') || ['tabindex','role','aria-label','aria-pressed'].includes(attr.name)) copies[i].removeAttribute(attr.name);
    }
    copies[i].style.removeProperty('cursor');
  });
  clone.style.removeProperty('width'); clone.style.removeProperty('height');
  clone.style.removeProperty('max-width'); clone.style.removeProperty('background');
  clone.removeAttribute('id'); clone.removeAttribute('class');
  clone.setAttribute('width','3000'); clone.setAttribute('height','3000');
  if (transparent) clone.querySelectorAll('.poster-halo, [data-background], .hol-svg-background').forEach(n => n.remove());
  else {
    const [x,y,w,h] = original.getAttribute('viewBox').split(/\s+/).map(Number);
    const bg = document.createElementNS('http://www.w3.org/2000/svg','rect');
    for (const [key,val] of Object.entries({x,y,width:w,height:h,fill:getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()||'#0f1220'})) bg.setAttribute(key,val);
    clone.insertBefore(bg,clone.firstChild);
  }
  return clone;
}
function telechargerBlob(blob, nom) {
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=nom; a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}
function exportPosterSVG() {
  const svg=document.getElementById('poster-svg');
  if (!svg.childElementCount) return;
  const clone=preparerSVGPoster(svg,document.getElementById('poster-fond-transparent').checked);
  const type=document.querySelector('input[name="poster-type"]:checked').value;
  telechargerBlob(new Blob([new XMLSerializer().serializeToString(clone)],{type:'image/svg+xml;charset=utf-8'}),`${type}-${slugPourFichier((DERNIER_RESULTAT._identite||{}).prenoms)}.svg`);
}
async function pngAvec300DPI(blob) {
  // PNG pHYs: 300 pixels per inch = 11,811 pixels per metre.
  const bytes=new Uint8Array(await blob.arrayBuffer());
  const chunk=new Uint8Array(21), view=new DataView(chunk.buffer);
  view.setUint32(0,9); chunk.set([112,72,89,115],4);
  view.setUint32(8,11811); view.setUint32(12,11811); chunk[16]=1;
  let crc=0xffffffff;
  for(const b of chunk.slice(4,17)){crc^=b;for(let k=0;k<8;k++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
  view.setUint32(17,(crc^0xffffffff)>>>0);
  const parts=[bytes.slice(0,8)];
  for(let offset=8;offset<bytes.length;){
    const size=new DataView(bytes.buffer,bytes.byteOffset+offset,4).getUint32(0)+12;
    const type=String.fromCharCode(...bytes.slice(offset+4,offset+8));
    if(type!=='pHYs')parts.push(bytes.slice(offset,offset+size));
    if(type==='IHDR')parts.push(chunk);
    offset+=size;
  }
  return new Blob(parts,{type:'image/png'});
}
document.getElementById('heure_inconnue').addEventListener('change',synchroniserHeure);
document.getElementById('heure_naissance').addEventListener('input',synchroniserHeure);
synchroniserHeure();
