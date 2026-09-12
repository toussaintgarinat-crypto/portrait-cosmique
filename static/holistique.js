(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const $svg = (tag, attrs = {}, texte) => {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v)));
    if (texte !== undefined) n.textContent = String(texte);
    return n;
  };
  const el = (tag, classe, texte) => {
    const n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texte !== undefined) n.textContent = String(texte);
    return n;
  };
  const langue = () => (typeof LANGUE !== "undefined" && LANGUE === "en" ? "en" : "fr");
  const tr = (fr, en) => (langue() === "en" ? en : fr);
  const valeur = (v, repli = "—") => (v === null || v === undefined || v === "" ? repli : String(v));

  const TEXTES = {
    fr: {
      titre: "Portrait holistique", intro: "Des repères symboliques issus de conventions distinctes, présentés sans valeur prédictive.",
      matrice: "Matrice de destinée", matriceAide: "Activez un point pour lire son arcane. La liste complète reste disponible sous le dessin.",
      axes: "Axes symboliques", principal1: "A–D · axe personnel", principal2: "B–C · axe généalogique", finances: "E–C · finances", amour: "E–D · amour",
      points: { A: "Portrait / jour", B: "Spiritualité / mois", C: "Matière / année", D: "Karma de l’âme", E: "Zone de confort" },
      bazi: "BaZi — quatre piliers", annee: "Année", mois: "Mois", jour: "Jour", heure: "Heure", maitre: "Maître du jour",
      elements: "Présence des cinq éléments", elementsNote: "Comptage visible des tiges et branches ; il ne mesure pas leur force.", polarites: "Yin et Yang",
      omissionBazi: "BaZi omis : l’heure de naissance et le décalage UTC sont nécessaires ; aucune heure artificielle n’est utilisée.",
      arbre: "Arbre de Vie", arbreNote: "Correspondance symbolique moderne", active: "Correspondance personnelle", potentiel: "Potentiel",
      maya: "Tzolkin maya", mayaNote: "Cycle traditionnel de 260 jours : 20 glyphes × 13 tonalités, distinct du Dreamspell.", kin: "Kin", glyphe: "Glyphe", tonalite: "Tonalité", convention: "Convention",
      vedique: "Lecture védique", longitude: "Longitude sidérale", pada: "Pada", ayanamsa: "Ayanamsa", precision: "Précision", rashi: "Rashi solaire",
      vediqueNote: "Position sidérale approchée selon un ayanamsa de Lahiri ; une proximité de frontière demande une éphéméride spécialisée.",
      celte: "Calendrier lunaire des 13 arbres", celteNote: "Calendrier moderne : 13 périodes de 28 jours et un jour intercalaire ; ce n’est pas un calendrier celtique historique universel.", periode: "Période", cycle: "Jour du cycle", intercalaire: "Jour intercalaire",
      numero: "Numérologie du nom", expression: "Expression", ame: "Âme", personnalite: "Personnalité", systeme: "Système",
      numeroNote: "L’expression utilise toutes les lettres, l’âme les voyelles et la personnalité les consonnes.", details: "Voir la lecture"
    },
    en: {
      titre: "Holistic portrait", intro: "Symbolic reference points from distinct conventions, presented without predictive claims.",
      matrice: "Destiny matrix", matriceAide: "Activate a point to read its arcana. The full list remains available below the drawing.",
      axes: "Symbolic axes", principal1: "A–D · personal axis", principal2: "B–C · ancestral axis", finances: "E–C · finances", amour: "E–D · love",
      points: { A: "Portrait / day", B: "Spirituality / month", C: "Matter / year", D: "Soul karma", E: "Comfort zone" },
      bazi: "BaZi — four pillars", annee: "Year", mois: "Month", jour: "Day", heure: "Hour", maitre: "Day master",
      elements: "Five element presence", elementsNote: "Visible count of stems and branches; it does not measure their strength.", polarites: "Yin and Yang",
      omissionBazi: "BaZi omitted: birth time and UTC offset are required; no artificial time is used.",
      arbre: "Tree of Life", arbreNote: "Modern symbolic correspondence", active: "Personal correspondence", potentiel: "Potential",
      maya: "Maya Tzolkin", mayaNote: "Traditional 260-day cycle: 20 glyphs × 13 tones, distinct from Dreamspell.", kin: "Kin", glyphe: "Glyph", tonalite: "Tone", convention: "Convention",
      vedique: "Vedic reading", longitude: "Sidereal longitude", pada: "Pada", ayanamsa: "Ayanamsa", precision: "Precision", rashi: "Solar rashi",
      vediqueNote: "Approximate sidereal position using a Lahiri ayanamsa; positions near a boundary require a specialised ephemeris.",
      celte: "Thirteen-tree lunar calendar", celteNote: "Modern calendar: thirteen 28-day periods and one intercalary day; it is not a universal historical Celtic calendar.", periode: "Period", cycle: "Cycle day", intercalaire: "Intercalary day",
      numero: "Name numerology", expression: "Expression", ame: "Soul urge", personnalite: "Personality", systeme: "System",
      numeroNote: "Expression uses all letters, soul urge the vowels, and personality the consonants.", details: "View reading"
    }
  };
  const T = () => TEXTES[langue()];

  const ELEMENTS_EN = {Bois:"Wood", Feu:"Fire", Terre:"Earth", Métal:"Metal", Eau:"Water"};
  const SEPH_EN = [
    ["Crown","direction and unity"],["Wisdom","creative impulse"],["Understanding","form and comprehension"],
    ["Kindness","expansion and generosity"],["Severity","boundaries and discernment"],["Beauty","coherence and harmony"],
    ["Victory","desire and endurance"],["Splendour","language and analysis"],["Foundation","connection and imagination"],["Kingdom","presence and realization"]
  ];
  const element = v => langue()==="en" ? (ELEMENTS_EN[v] || valeur(v)) : valeur(v);
  const sephLabel = s => langue()==="en" ? (SEPH_EN[s.numero-1]||[])[0] || s.nom : s.nom_fr;
  const sephSens = s => langue()==="en" ? (SEPH_EN[s.numero-1]||[])[1] || "" : s.potentiel;
  const sourceLabel = k => langue()==="en" ? ({date:"date",nom:"name",combinaison:"combination"}[k]||k) : k;

  function aide(parent, id) {
    if (!id || typeof icGlossaire !== "function") return parent;
    const html = icGlossaire(id);
    if (html) parent.insertAdjacentHTML("beforeend", html);
    return parent;
  }

  function aideLibelle(texte) {
    const t = T();
    return new Map([
      [t.matrice,"matrice_destinee"], [t.bazi,"bazi"], [t.arbre,"arbre_vie"],
      [t.maya,"maya"], [t.vedique,"vedique"], [t.celte,"celte_13"], [t.numero,"numerologie_nom"],
      [t.maitre,"bazi_maitre"], [t.elements,"bazi_elements"], [t.polarites,"bazi_polarites"],
      [t.kin,"maya_kin"], [t.glyphe,"maya"], [t.tonalite,"maya_tonalite"],
      ["Nakshatra","nakshatra"], [t.pada,"vedique_pada"], [t.ayanamsa,"vedique_ayanamsa"],
      [t.rashi,"vedique"], [t.expression,"expression"], [t.ame,"numerologie_ame"],
      [t.personnalite,"numerologie_personnalite"]
    ]).get(texte);
  }

  function titreCarte(texte, note) {
    const h = el("div", "hol-titre");
    h.append(aide(el("h3", "", texte), aideLibelle(texte)));
    if (note) h.append(el("p", "hol-note", note));
    return h;
  }

  function paire(parent, libelle, contenu) {
    const d = el("div", "hol-paire");
    d.append(aide(el("span", "hol-cle", libelle), aideLibelle(libelle)), el("strong", "hol-valeur", valeur(contenu)));
    parent.append(d);
  }

  function detailsCarte(titre, note, ouverte = false) {
    const d = el("details", "hol-carte hol-details");
    d.open = ouverte;
    const s = el("summary", "hol-summary");
    const bloc = el("span");
    bloc.append(aide(el("span", "hol-summary-titre", titre), aideLibelle(titre)));
    if (note) bloc.append(el("span", "hol-summary-note", note));
    s.append(bloc, el("span", "hol-chevron", "›"));
    d.append(s);
    return d;
  }

  function dessinerMatrice(svg, matrice, options = {}) {
    if (!svg) return;
    const { interactif = false, identite = {} } = options;
    const points = (matrice && matrice.points) || {};
    const arcanes = (matrice && matrice.arcanes) || {};
    const roles = T().points;
    const pos = { A: [82, 220], B: [220, 82], C: [358, 220], D: [220, 358], E: [220, 220] };
    svg.replaceChildren();
    svg.setAttribute("viewBox", "0 0 440 440");
    svg.setAttribute("role", interactif ? "group" : "img");
    svg.setAttribute("aria-label", `${T().matrice}${identite.prenoms ? ` — ${identite.prenoms}` : ""}`);
    svg.append($svg("rect", { class: "hol-svg-background", x: 1, y: 1, width: 438, height: 438, rx: 18, fill: "#111526", stroke: "#333a5e" }));
    const lines = [
      ["82,220 220,82 358,220 220,358", "#b98cf7", 1.5],
      ["122,122 318,122 318,318 122,318", "#6ee7c3", 1.2]
    ];
    lines.forEach(([pts, stroke, width]) => svg.append($svg("polygon", { points: pts, fill: "none", stroke, "stroke-width": width, opacity: .78 })));
    [[82, 220, 220, 358], [220, 82, 358, 220]].forEach(([x1, y1, x2, y2]) =>
      svg.append($svg("line", { x1, y1, x2, y2, stroke: "#7780a8", "stroke-width": 1, "stroke-dasharray": "4 5", opacity: .72 })));
    [[220, 220, 358, 220], [220, 220, 220, 358]].forEach(([x1, y1, x2, y2], i) =>
      svg.append($svg("line", { x1, y1, x2, y2, stroke: i ? "#e1a76c" : "#6ee7c3", "stroke-width": 2, opacity: .9 })));
    const axisLabels = [[220,22,T().matrice],[140,402,T().principal1],[310,402,T().principal2]];
    axisLabels.forEach(([x,y,label]) => svg.append($svg("text", { x, y, fill: "#aab0cc", "font-size": 9, "font-family": "system-ui, sans-serif", "text-anchor": "middle" }, label)));
    const signature = [identite.prenoms, identite.nom].filter(Boolean).join(" ");
    if (signature) svg.append($svg("text", {x:220,y:425,fill:"#f4f1ff","font-size":Math.min(12,360/Math.max(signature.length,1)*1.5),"font-family":"Georgia, serif","text-anchor":"middle"}, signature));
    Object.entries(pos).forEach(([cle, [x, y]]) => {
      const g = $svg("g", { "data-point": cle });
      if (interactif) {
        g.setAttribute("role", "button"); g.setAttribute("tabindex", "0");
        g.setAttribute("aria-label", `${cle}, ${roles[cle]}, ${valeur(points[cle])}`);
      }
      g.append($svg("circle", { cx: x, cy: y, r: cle === "E" ? 35 : 31, fill: cle === "E" ? "#29234a" : "#1d2239", stroke: cle === "E" ? "#e1a76c" : "#b98cf7", "stroke-width": 2 }));
      g.append($svg("text", { x, y: y - 7, fill: "#9aa1c4", "font-size": 10, "font-weight": 700, "font-family": "system-ui, sans-serif", "text-anchor": "middle" }, cle));
      g.append($svg("text", { x, y: y + 14, fill: "#f4f1ff", "font-size": 22, "font-weight": 700, "font-family": "Georgia, serif", "text-anchor": "middle" }, valeur(points[cle])));
      if (interactif) {
        const activer = () => svg.dispatchEvent(new CustomEvent("matrice-point", { detail: { cle, arcane: arcanes[cle] || {} } }));
        g.addEventListener("click", activer);
        g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activer(); } });
      }
      svg.append(g);
    });
  }

  function dessinerArbre(svg, arbre) {
    if (!svg) return;
    const seph = (arbre && arbre.sephiroth) || [];
    const pos = [[210,35],[130,90],[290,90],[105,160],[315,160],[210,205],[110,270],[310,270],[210,325],[210,395]];
    svg.replaceChildren(); svg.setAttribute("viewBox", "0 0 420 430"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", T().arbre);
    svg.append($svg("rect", { x:1,y:1,width:418,height:428,rx:18,fill:"#111526",stroke:"#333a5e" }));
    [[0,1],[0,2],[1,2],[1,3],[1,5],[2,4],[2,5],[3,4],[3,5],[3,6],[4,5],[4,7],[5,6],[5,7],[5,8],[6,7],[6,8],[7,8],[8,9]].forEach(([a,b]) => {
      const p=pos[a], q=pos[b]; svg.append($svg("line",{x1:p[0],y1:p[1],x2:q[0],y2:q[1],stroke:"#454d72","stroke-width":1}));
    });
    pos.forEach(([x,y], i) => {
      const s=seph[i] || {}, active=Array.isArray(s.active_par)&&s.active_par.length;
      svg.append($svg("circle",{cx:x,cy:y,r:24,fill:active?"#342755":"#1d2239",stroke:active?"#e1a76c":"#6ee7c3","stroke-width":active?3:1.5}));
      svg.append($svg("text",{x,y:y-2,fill:"#f4f1ff","font-size":10,"font-weight":700,"font-family":"system-ui, sans-serif","text-anchor":"middle"},s.nom || i+1));
      svg.append($svg("text",{x,y:y+11,fill:"#aab0cc","font-size":8,"font-family":"system-ui, sans-serif","text-anchor":"middle"},sephLabel(s) || ""));
    });
  }

  function carteMatrice(m) {
    const card = el("section", "hol-carte hol-matrice");
    card.append(titreCarte(T().matrice, T().matriceAide));
    const svg = $svg("svg", { id: "matrice-svg", class: "hol-svg" });
    const detail = el("div", "hol-arcane-actif");
    detail.setAttribute("aria-live", "polite");
    const montrer = (cle) => {
      const a=(m.arcanes||{})[cle]||{};
      detail.replaceChildren(el("strong", "", `${cle} · ${valeur(a[`nom_${langue()}`], valeur(a.nom_fr))}`), el("span", "", valeur(a[`sens_${langue()}`], valeur(a.sens_fr))));
      svg.querySelectorAll("[data-point]").forEach(n => n.classList.toggle("is-active", n.dataset.point===cle));
    };
    svg.addEventListener("matrice-point", e => montrer(e.detail.cle));
    dessinerMatrice(svg, m, { interactif:true }); card.append(svg, detail);
    montrer("E");
    const liste = el("div", "hol-arcanes-liste");
    ["A","B","C","D","E"].forEach(c => { const a=(m.arcanes||{})[c]||{}; const b=el("button","hol-arcane-bouton"); b.type="button"; b.append(el("span","hol-arcane-num",`${c} · ${valeur((m.points||{})[c])} · ${T().points[c]}`),el("span","",valeur(a[`nom_${langue()}`],a.nom_fr)),el("small","",valeur(a[`sens_${langue()}`],a.sens_fr))); b.addEventListener("click",()=>montrer(c)); const item=el("div","hol-arcane-item"); item.append(b); aide(item,`matrice_${c}`); liste.append(item); });
    card.append(liste);
    const leg = el("div","hol-legende"); [[T().principal1,"matrice_personnel"],[T().principal2,"matrice_genealogique"],[T().finances,"matrice_finances"],[T().amour,"matrice_amour"]].forEach(([x,id])=>leg.append(aide(el("span","",x),id))); card.append(leg);
    const methode = el("details", "hol-methode");
    methode.append(el("summary", "", tr("Comprendre le calcul et les axes", "Understand the calculation and axes")), el("p", "hol-note", tr(
      "A = jour réduit ; B = mois ; C = somme réduite des chiffres de l’année ; D = réduction de A+B+C ; E = réduction de A+B+C+D. Au-delà de 22, on additionne les chiffres jusqu’à obtenir 1 à 22. Ce n’est pas un modulo. Les arcanes suivent ici Marseille : Justice VIII, Force XI, Le Mat conventionnellement 22.",
      "A = reduced day; B = month; C = reduced sum of the year’s digits; D = reduction of A+B+C; E = reduction of A+B+C+D. Above 22, add the digits until reaching 1–22. This is not a modulo. Marseille numbering is used: Justice VIII, Strength XI and The Fool assigned 22."
    )), el("p", "hol-note", tr("A–D : lecture personnelle, ciel/esprit. B–C : lecture généalogique, terre/matière. E–C et E–D sont des axes de réflexion sur les ressources et les relations, sans score financier ni prédiction amoureuse.", "A–D: personal reading, sky/spirit. B–C: ancestral reading, earth/matter. E–C and E–D invite reflection on resources and relationships, without financial scores or relationship predictions.")));
    card.append(methode);
    return card;
  }

  function carteBazi(b) {
    const d=detailsCarte(T().bazi,tr(b.convention,"Civil birth time and UTC offset; solar year at Li Chun, months at jie, day rollover at midnight, no apparent solar-time correction."));
    const grille=el("div","hol-piliers"); ["annee","mois","jour","heure"].forEach(k=>{const p=(b.piliers||{})[k]||{}, c=el("div","hol-pilier"); c.append(aide(el("span","hol-cle",T()[k]),"bazi_piliers"),el("strong","hol-ganzhi",valeur(p.gan_zhi)),el("span","",valeur(p.romanise)),el("small","",`${element(p.tige&&p.tige.element)} · ${valeur(p.tige&&p.tige.polarite)}`)); grille.append(c);});
    d.append(grille); const master=el("div","hol-master"); paire(master,T().maitre,`${valeur(b.maitre_du_jour&&b.maitre_du_jour.caractere)} ${valeur(b.maitre_du_jour&&b.maitre_du_jour.nom)} · ${element(b.maitre_du_jour&&b.maitre_du_jour.element)} ${valeur(b.maitre_du_jour&&b.maitre_du_jour.polarite)}`); d.append(master);
    const counts=el("div","hol-counts"); counts.append(aide(el("h4","",T().elements),"bazi_elements"),el("p","hol-note",T().elementsNote)); Object.entries(b.elements||{}).forEach(([k,v])=>{const row=el("div","hol-count-row"); row.append(el("span","",element(k)),el("span","hol-dots",Array(Math.max(0,Number(v))+1).join("●")),el("strong","",v)); counts.append(row);});
    counts.append(aide(el("h4","hol-subhead",T().polarites),"bazi_polarites")); Object.entries(b.polarites||{}).forEach(([k,v])=>paire(counts,k,v)); d.append(counts);
    if(b.precision){const p=el("p","hol-convention"); p.textContent=`${tr(valeur(b.precision.termes_solaires),"Approximate solar longitude; verify near a boundary")} · ${valeur(b.precision.longitude_solaire)}°${b.precision.limite_proche?tr(" · frontière proche : pilier à vérifier"," · near a boundary: verify this pillar"):""}`; d.append(p);} return d;
  }

  function carteArbre(a) { const d=detailsCarte(T().arbre,T().arbreNote); const svg=$svg("svg",{class:"hol-svg hol-arbre-svg"}); dessinerArbre(svg,a); d.append(svg); const ul=el("ul","hol-seph-list"); (a.sephiroth||[]).forEach(s=>{const li=el("li",s.active_par&&s.active_par.length?"active":""); li.append(aide(el("strong","",`${s.numero}. ${s.nom} · ${sephLabel(s)}`),"arbre_sephiroth"),el("span","",`${T().potentiel} : ${valeur(sephSens(s))}`)); if(s.active_par&&s.active_par.length)li.append(el("em","",`${T().active} : ${s.active_par.map(sourceLabel).join(", ")}`)); ul.append(li);}); d.append(ul,el("p","hol-convention",tr(valeur(a.convention),"Modern symbolic mapping: reduce the date and Latin-alphabet name to 1–10, using the cyclic 1–9 alphabet. This is not a universal Kabbalistic method or Hebrew gematria. Lines show a schematic layout, not calculated personal trials."))); return d; }

  function carteSimple(titre,note,items,convention) { const d=detailsCarte(titre,note); const g=el("div","hol-faits"); items.filter(x=>x[1]!==undefined&&x[1]!==null&&x[1]!=="").forEach(x=>paire(g,x[0],x[1])); d.append(g); if(convention)d.append(el("p","hol-convention",convention)); return d; }

  function rendreHolistique(d) {
    const racine=document.getElementById("r-holistique");
    const matrice=document.getElementById("r-matrice");
    const trad=(d&&d.traditions)||{}; const hol=(d&&d.holistique)||trad.holistique||trad;
    if(matrice) { matrice.replaceChildren(); if(hol.matrice_destinee)matrice.append(carteMatrice(hol.matrice_destinee)); }
    if(!racine)return;
    racine.replaceChildren();
    if(hol.bazi)racine.append(carteBazi(hol.bazi)); else racine.append(aide(el("p","hol-omission",T().omissionBazi),"bazi"));
    if(hol.arbre_vie)racine.append(carteArbre(hol.arbre_vie));
    const sens = id => ((d.empreinte||[]).find(e=>e.id===id)||{}).sens || "";
    const maya=trad.maya;
    if(maya){
      const card=carteSimple(T().maya,T().mayaNote,[[T().kin,maya.kin],[T().glyphe,maya.glyphe],[T().tonalite,`${maya.tonalite} / 13`],[tr("Lecture du glyphe","Glyph reading"),sens("maya")]],tr(maya.convention,T().mayaNote));
      const tones=el("div","hol-cycle");tones.setAttribute("aria-label",T().tonalite);
      for(let i=1;i<=13;i++){const n=el("span",i===maya.tonalite?"active":"",i);if(i===maya.tonalite)n.setAttribute("aria-current","true");tones.append(n);} card.append(tones);
      const glyphes=["Imix","Ik","Akbal","Kan","Chicchan","Cimi","Manik","Lamat","Muluc","Oc","Chuen","Eb","Ben","Ix","Men","Cib","Caban","Etznab","Cauac","Ahau"];
      const grid=el("div","hol-glyphes");glyphes.forEach((g,i)=>{const n=el("span",g===maya.glyphe?"active":"",`${i+1} · ${g}`);if(g===maya.glyphe)n.setAttribute("aria-current","true");grid.append(n);});card.append(grid);racine.append(card);
    }
    const nk=trad.nakshatra, ved=trad.vedique; if(nk||ved)racine.append(carteSimple(T().vedique,T().vediqueNote,[["Nakshatra",nk&&nk.nakshatra],[T().pada,nk&&nk.pada!=null?`${nk.pada} / 4`:null],[tr("Lecture symbolique","Symbolic reading"),sens("nakshatra")],[T().longitude,nk&&nk.longitude_siderale!=null?`${nk.longitude_siderale}°`:null],[T().rashi,ved&&ved.rashi],[T().ayanamsa,nk&&nk.ayanamsa!=null?`${nk.ayanamsa}° (Lahiri ≈)`:null],[T().precision,nk?tr(nk.precision,T().vediqueNote):null]],nk&&nk.convention));
    else racine.append(aide(el("p","hol-omission",tr("Nakshatra indisponible sans heure de naissance : aucune position lunaire n’est inventée.","Nakshatra unavailable without birth time: no lunar position is invented.")),"vedique"));
    const cel=hol.celte_lunaire; if(cel)racine.append(carteSimple(T().celte,T().celteNote,[[tr("Arbre","Tree"),cel.arbre?`${cel.arbre}${langue()==="en"&&cel.nom_en?` · ${cel.nom_en}`:""}`:T().intercalaire],[T().periode,cel.periode],[T().cycle,cel.jour_cycle],[tr("Autre convention : 21 arbres (synthèse)","Other convention: 21 trees (synthesis)"),trad.celte],[tr("Lecture de cette autre convention","Reading for this other convention"),sens("celte")]],tr(cel.convention,T().celteNote)));
    const num=trad.numerologie_nom; if(num)racine.append(carteSimple(T().numero,T().numeroNote,[[T().expression,num.expression],[tr("Sens de l’expression","Expression reading"),sens("expression")],[T().ame,num.ame],[T().personnalite,num.personnalite],[T().systeme,num.systeme]]));
  }

  window.rendreHolistique=rendreHolistique;
  window.dessinerMatrice=dessinerMatrice;
  window.dessinerArbre=dessinerArbre;
})();
