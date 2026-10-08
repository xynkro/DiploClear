global.window = global.window || global; global.self = global.window;
const {DOMParser,XMLSerializer}=require("@xmldom/xmldom"); global.DOMParser=DOMParser; global.XMLSerializer=XMLSerializer; window.DOMParser=DOMParser; window.XMLSerializer=XMLSerializer;

const DC="/Users/xynkro/Documents/DiploClear";
const fs=require('fs');
require(DC+"/lib/pizzip.js"); const PizZip=window.PizZip;
require(DC+"/lib/docxtemplater.js"); const DT=window.docxtemplater;
const PL=require(DC+"/lib/pdf-lib.js"); const PDFLib=(PL&&PL.PDFDocument)?PL:window.PDFLib;
require(DC+"/lib/templates_data.js"); const TEMPLATES=window.TEMPLATES;
const html=fs.readFileSync(DC+"/index.html","utf8");
const ev=(re,label)=>{ const m=html.match(re); if(!m){console.log("!! extract fail",label); return null;} return eval('('+m[1]+')'); };
const COUNTRIES=ev(/const COUNTRIES\s*=\s*(\[[\s\S]*?\]);/,"COUNTRIES");
const TPL=ev(/const TPL\s*=\s*(\{[^;]*?\});/,"TPL");
const XTPL=ev(/const XTPL\s*=\s*(\{[^;]*?\});/,"XTPL");
const PTPL=ev(/const PTPL\s*=\s*(\{[^;]*?\});/,"PTPL");
const XBLANK=ev(/const XBLANK\s*=\s*(\{[^;]*?\});/,"XBLANK");
const PDFMAP=ev(/const PDFMAP\s*=\s*(\{[\s\S]*?\]\}\});/,"PDFMAP");
const data={dcr_no:"042-26 (1)",dtd:"13 AUG 26",date:"08 APR 26",aircraft:"1 x C-130",type:"C-130",
 tails:"735 (ALT: 736)",callsign:"SINGA 12",reg:"735",sector:"PAYA LEBAR - DARWIN",route:"CHANGI — TIDAR — DARWIN",
 dest:"DARWIN",time_note:"(ALL TIMES UTC)",etd:"08 APR 26",eta:"08 APR 26",purpose:"Exercise deployment",
 in_support:"Exercise deployment",captain:"DERIC JIA HAO",crew_n:"9",crew:"DERIC JIA HAO + 8 CREW",pax:"24",
 cargo:"PERSONAL BAGGAGE & FAK",mil_equip:"NIL",photo:"NIL",services:"NIL",validity:"72 HOURS",
 level:"FL 250 - 390",dep:"PAYA LEBAR",other:"NIL",remarks:"REQUEST FLIGHT CLEARANCE VALID 72 HOURS."};
function genDoc(k){ const doc=new DT(new PizZip(TEMPLATES[k],{base64:true}),{paragraphLoop:true,linebreaks:true}); doc.render(data); return doc.getZip().generate({type:"nodebuffer"}); }
function genXlsx(k){ const zip=new PizZip(TEMPLATES[k],{base64:true}); const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
 (zip.file(/xl\/(worksheets\/.*|sharedStrings)\.xml/)||[]).forEach(f=>{let s=f.asText(); for(const kk in data) s=s.split("{"+kk+"}").join(esc(data[kk])); zip.file(f.name,s);}); return zip.generate({type:"nodebuffer"}); }
async function genPdf(k){ const {PDFDocument,rgb,StandardFonts}=PDFLib; const pdf=await PDFDocument.load(Uint8Array.from(Buffer.from(TEMPLATES[k],"base64")),{ignoreEncryption:true,throwOnInvalidObject:false});
 const font=await pdf.embedFont(StandardFonts.Helvetica); const pages=pdf.getPages(); const pg=i=>pages[(i||1)-1]||pages[0];
 for(const b of (PDFMAP[k].blanks||[])){const p=pg(b.page),H=p.getHeight(); p.drawRectangle({x:b.x,y:H-b.bot-1,width:b.w,height:(b.bot-b.top)+2,color:rgb(1,1,1)});}
 for(const f of PDFMAP[k].fields){const p=pg(f.page),H=p.getHeight(); const val=f.text!=null?f.text:String(data[f.key]??"");
   if(f.ty!=null) p.drawText(val,{x:f.x,y:f.ty,size:f.size||9,font,color:rgb(.05,.05,.05)});
   else{p.drawRectangle({x:f.x,y:H-f.bot-1,width:f.w,height:(f.bot-f.top)+2,color:rgb(1,1,1)}); p.drawText(val,{x:f.x+1.5,y:H-f.bot+2.5,size:f.size,font,color:rgb(.05,.05,.05)});}}
 return Buffer.from(await pdf.save()); }
(async()=>{
 const rows=[]; let ok=0; const bundle=[];   // bundle = what "Download all" packs into the ZIP
 for(const c of COUNTRIES){ const iso=c.iso; let route,buf,err;
   try{
     if(TPL[iso]){route="docx"; buf=genDoc(TPL[iso]);}
     else if(XTPL[iso]){route="xlsx"; buf=genXlsx(XTPL[iso]);}
     else if(PTPL[iso]){route="pdf"; buf=await genPdf(PTPL[iso]);}
     else if(XBLANK[iso]){route="blank-pdf"; buf=Buffer.from(TEMPLATES[XBLANK[iso]],"base64");}
     else {route="NONE";}
   }catch(e){err=e.message;}
   if(buf&&route.includes("pdf")) fs.writeFileSync("/tmp/gen_"+iso+".pdf", buf);
   if(buf){ const cs=data.callsign.replace(/ /g,''), dt=data.date.replace(/ /g,'');
     const ext = route==="xlsx"?"xlsx":(route.includes("pdf")?"pdf":"docx");
     bundle.push({name: route==="blank-pdf" ? `${c.nm}_form_to_complete.pdf` : `${c.nm}_${cs}_${dt}_v1.${ext}`, buf}); }
   const kb=buf?Math.round(buf.length/1024):0; if(buf&&buf.length>500&&!err) ok++;
   rows.push(`${c.nm.padEnd(13)} ${iso} ${route.padEnd(9)} ${String(kb).padStart(5)}KB ${err?('ERR '+err):'ok'}`);
 }
 console.log("Extracted:", {COUNTRIES:COUNTRIES.length, TPL:Object.keys(TPL).length, XTPL:Object.keys(XTPL).length, PTPL:Object.keys(PTPL).length, XBLANK:Object.keys(XBLANK).length});
 console.log(rows.join("\n"));
 console.log(`\n==> ${ok}/${COUNTRIES.length} generated a valid non-empty file`);
 console.log("LEAKWORDS check runs separately via pdftotext");

 // ---- verify the "Download all" archive the browser builds from these same buffers ----
 const zip=new PizZip();
 for(const f of bundle) zip.file(f.name, f.buf);
 const out=zip.generate({type:"nodebuffer"});
 const names=bundle.map(f=>f.name);
 const dupes=names.filter((n,i)=>names.indexOf(n)!==i);
 const rt=new PizZip(out);                       // read it back the way a recipient would
 const back=Object.keys(rt.files);
 const empty=back.filter(n=>rt.file(n).asUint8Array().length===0);
 console.log(`\nARCHIVE  files=${bundle.length}  reopened=${back.length}  dupes=${dupes.length}  empty=${empty.length}  size=${(out.length/1048576).toFixed(2)}MB`);
 if(dupes.length) console.log("  DUPLICATE NAMES:", dupes);
 if(empty.length) console.log("  EMPTY MEMBERS:", empty);
 const bad = bundle.length!==COUNTRIES.length || back.length!==COUNTRIES.length || dupes.length || empty.length;
 console.log(bad ? "==> ARCHIVE FAILED" : `==> ARCHIVE OK — all ${COUNTRIES.length} forms present, unique, non-empty`);
 fs.writeFileSync("/tmp/DiploClear_all21.zip", out);
})();

// ---- invariant: Australia must ship as a LIVE form, filled, with nothing left over -----
// Australia will not accept the flattened render. The AF179 has to stay an Adobe LiveCycle
// form (/XFA + /NeedsRendering) with the mission written into its datasets packet. Three ways
// that silently breaks: the packet gets recompressed (the runtime then decodes deflate as
// UTF-8 and destroys it), a marker has no mission field behind it, or the scrub stops running
// and the sample sortie rides along.
(() => {
  const fails = [];
  const b64 = TEMPLATES["australia_xfa"];
  if(!b64){ fails.push("australia_xfa template is not bundled"); }
  else {
    const buf = Buffer.from(b64, "base64");
    const raw = buf.toString("latin1");
    if(!/\/NeedsRendering\s*true/.test(raw)) fails.push("template lost /NeedsRendering — Adobe will not treat it as a form");
    if(!/\/AcroForm/.test(raw))               fails.push("template lost /AcroForm");
    // the datasets packet must still be plain XML, or the runtime substitution corrupts it
    const i = raw.indexOf("<xfa:datasets");
    if(i < 0) fails.push("datasets packet is not plain XML in the bundle — patch_tpl.py must save with compress_streams=False");
    else {
      const seg = raw.slice(i, raw.indexOf("</xfa:datasets>", i) + 15);
      const markers = [...new Set([...seg.matchAll(/\[\[(\w+)\]\]/g)].map(m => m[1]))];
      if(!markers.length) fails.push("datasets packet carries no [[markers]] — nothing would be filled");
      // every marker must have a field behind it in buildData()
      const bd = html.slice(html.indexOf("function buildData()"), html.indexOf("\n  }", html.indexOf("function buildData()")));
      const positional = /p\$\{i\+1\}_|p\${i\+1}_/.test(bd) || /`p\$\{i \+ 1\}_/.test(bd) || bd.includes("p${i+1}_pt");
      const orphan = markers.filter(m => {
        if(/^p[1-6]_(pt|fir|eta|etd|etaz|etdz)$/.test(m)) return !positional;
        // buildData uses both "name: value" and ES6 shorthand "name,", so accept either
        return !new RegExp("(^|[\\s{,])" + m + "\\s*[:,]").test(bd);
      });
      if(orphan.length) fails.push("markers with no mission field: " + orphan.join(", "));
      console.log(`\nAUSTRALIA-LIVE-XFA  markers=${markers.length}  orphans=${orphan.length}${orphan.length? ' ('+orphan.join(', ')+')':''}`);
      // control: a marker that genuinely has no field behind it must be caught
      const bogus = "definitely_not_a_mission_field";
      const caught = !new RegExp("(^|[\\s{,])" + bogus + "\\s*[:,]").test(bd);
      console.log(caught ? "    control: a marker with no mission field IS caught"
                         : "    !! CONTROL FAILED — orphan detection is blind");
    }
  }
  console.log(fails.length ? "==> AUSTRALIA-LIVE-XFA FAILED\n    - " + fails.join("\n    - ")
                           : "==> AUSTRALIA-LIVE-XFA OK — live form, plain datasets, every marker backed by a field");
})();

// ---- invariant: no template may name a person in its document metadata ----------------
// Body text was always scrubbed; docProps never was. Twelve templates carried
// "Ronnie, SO2 DPCS, AOCG" as last-modified-by, which travelled to twelve host nations on
// every request. Nobody opens File > Properties, which is why it survived the audits.
(() => {
  const TAGS=["dc:creator","cp:lastModifiedBy","Company","Manager"];
  const named=[];
  for(const k of Object.keys(TEMPLATES)){
    const b=Buffer.from(TEMPLATES[k],"base64");
    if(b.slice(0,2).toString()!=="PK") continue;          // PDFs carry no docProps
    let z; try{ z=new PizZip(b); }catch(e){ continue; }
    for(const fn of ["docProps/core.xml","docProps/app.xml"]){
      const f=z.file(fn); if(!f) continue;
      const x=f.asText();
      for(const tag of TAGS){
        const m=x.match(new RegExp("<"+tag+"[^>]*>([^<]+)</"+tag+">"));
        if(m && m[1].trim()) named.push(`${k}:${tag.split(":").pop()}=${m[1].trim()}`);
      }
    }
  }
  console.log(`\nNO-AUTHOR-METADATA  office templates scanned=${Object.keys(TEMPLATES).length}  naming a person=${named.length}`);
  console.log(named.length ? "==> NO-AUTHOR-METADATA FAILED\n    - " + named.join("\n    - ")
                           : "==> NO-AUTHOR-METADATA OK — no creator, editor or company left in any template");
  const ctl = '<dc:creator>Ronnie, SO2 DPCS, AOCG</dc:creator>'.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/);
  console.log(ctl && ctl[1].trim() ? "    control: a named creator IS caught"
                                   : "    !! CONTROL FAILED — the scan is blind");
})();

// ---- invariant: no template may ship another mission's dates or times -----------------
// Four templates used to carry the sample sortie's itinerary as static text: India told India
// we were flying Riyadh-Singapore on 10 MAR, Thailand printed a fixed 08/2300Z Apr 26 table,
// Malaysia 07 APR, Egypt entry SALUN 1405Z. They were filed on every request regardless of the
// real mission. Dates and times must come from the entered itinerary, never from the template.
(() => {
  const DOCX={IDN:'indonesia',THA:'thailand',VNM:'vietnam',MYS:'malaysia',KHM:'cambodia',MMR:'myanmar',
              SAU:'saudi',TWN:'taiwan',GRC:'greece',ESP:'spain',ITA:'italy',DEU:'germany',
              EGY:'egypt',OMN:'oman',IND:'india'};
  const RX=/\b\d{1,2}\s?\d?\s*\/?\s*\d{0,2}\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b|\b\d{2}\s?\d{2}\s*(UTC|Z)\b/gi;
  const bad=[];
  for(const [iso,k] of Object.entries(DOCX)){
    const z=new PizZip(TEMPLATES[k],{base64:true}); let x='';
    (z.file(/word\/(document|header\d*|footer\d*)\.xml/)||[]).forEach(f=>x+=f.asText());
    const t=x.replace(/<[^>]+>/g,'').replace(/\s+/g,' ');
    const hits=[...new Set((t.match(RX)||[]).map(h=>h.trim()))];
    if(hits.length) bad.push(`${iso}: ${hits.join(', ')}`);
  }
  console.log(`\nNO-BAKED-DATES  templates scanned=${Object.keys(DOCX).length}  carrying sample dates/times=${bad.length}`);
  console.log(bad.length ? "==> NO-BAKED-DATES FAILED\n    - " + bad.join("\n    - ")
                         : "==> NO-BAKED-DATES OK — every date and time comes from the entered itinerary");
  // positive control: a template that really does carry one must be caught
  const ctl = "<w:t>Entry Point: REXOD @ 1245Z</w:t><w:t> on 10 MAR 26</w:t>".replace(/<[^>]+>/g,' ');
  const got = [...new Set((ctl.match(RX)||[]).map(h=>h.trim()))];
  console.log(got.length>=2 ? `    control: a baked itinerary IS caught (${got.join(', ')})`
                            : `    !! CONTROL FAILED — the scan is blind (matched ${got.length})`);
})();

// ---- invariant: strip, sign-off and emitted file must describe ONE frozen mission ----
// Regression guard for the late-edit bug: generating with SINGA 12, signing off, then
// changing the callsign used to emit a HERON 99 document from a strip still badged
// "reviewed · <name>". Every generation path must read the frozen batch, never the inputs.
// Scoped to the engines themselves — buildData() and saveMission() read live fields by design.
function frozenMissionCheck(src){
  const fails = [];
  const ENGINES = ["generateDoc","generateXlsx","generatePdf","downloadFlatBlank","downloadAll"];
  for(const fn of ENGINES){
    const i = src.indexOf("function "+fn+"("), j = src.indexOf("\n  }", i);   // to its closing brace
    if(i < 0){ fails.push(`engine ${fn}() not found`); continue; }
    const body = src.slice(i, j);
    if(/buildData\(\)/.test(body))  fails.push(`${fn}() rebuilds the mission from live inputs — use activeData()`);
    if(/fld\('f_/.test(body))        fails.push(`${fn}() reads a live input field — use activeData()/nameStem()`);
  }
  // preview must run the SAME engine as download, over the same freeze — a preview built by
  // any other path could show something the recipient never receives
  if(!/async function openPreview\(/.test(src)) fails.push("openPreview() missing");
  else {
    const i=src.indexOf("async function openPreview("), body=src.slice(i, src.indexOf("\n  }", i));
    if(!/await dlOne\(/.test(body))      fails.push("openPreview() does not go through dlOne() — it could diverge from Download");
    if(/buildData\(\)/.test(body))      fails.push("openPreview() rebuilds the mission from live inputs");
    if(!/activeData\(\)/.test(body))    fails.push("openPreview() office table does not read the freeze");
  }
  // openVerify shows the operator what they are putting their name to: must be the freeze
  if(!/const d=activeData\(\), f=freshness/.test(src)) fails.push("verify modal still reads live fields");
  for(const [re,what] of [[/let BATCH\s*=/,"BATCH freeze"],[/function activeData\(/,"activeData()"],
                          [/function missionSig\(/,"missionSig()"],[/function checkDrift\(/,"checkDrift()"],
                          [/BATCH\s*=\s*\{\s*data:d/,"generate() stores the freeze"]])
    if(!re.test(src)) fails.push(`missing ${what}`);
  return fails;
}
(() => {
  const fails = frozenMissionCheck(html);
  console.log(`\nFROZEN-MISSION  engines checked=5  violations=${fails.length}`);
  console.log(fails.length ? "==> FROZEN-MISSION FAILED\n    - " + fails.join("\n    - ")
                           : "==> FROZEN-MISSION OK — strip, sign-off and file all read one frozen mission");
  // positive control: re-introducing the bug in a copy of the source must be caught
  const bugged = html.replace("doc.render(activeData());","doc.render(buildData());");
  const caught = frozenMissionCheck(bugged).length > fails.length;
  console.log(caught ? "    control: reintroducing buildData() in generateDoc IS caught"
                     : "    !! CONTROL FAILED — the check is blind, fix it before trusting it");
})();
