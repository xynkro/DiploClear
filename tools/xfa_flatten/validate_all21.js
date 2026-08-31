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
 const rows=[]; let ok=0;
 for(const c of COUNTRIES){ const iso=c.iso; let route,buf,err;
   try{
     if(TPL[iso]){route="docx"; buf=genDoc(TPL[iso]);}
     else if(XTPL[iso]){route="xlsx"; buf=genXlsx(XTPL[iso]);}
     else if(PTPL[iso]){route="pdf"; buf=await genPdf(PTPL[iso]);}
     else if(XBLANK[iso]){route="blank-pdf"; buf=Buffer.from(TEMPLATES[XBLANK[iso]],"base64");}
     else {route="NONE";}
   }catch(e){err=e.message;}
   if(buf&&route.includes("pdf")) fs.writeFileSync("/tmp/gen_"+iso+".pdf", buf);
   const kb=buf?Math.round(buf.length/1024):0; if(buf&&buf.length>500&&!err) ok++;
   rows.push(`${c.nm.padEnd(13)} ${iso} ${route.padEnd(9)} ${String(kb).padStart(5)}KB ${err?('ERR '+err):'ok'}`);
 }
 console.log("Extracted:", {COUNTRIES:COUNTRIES.length, TPL:Object.keys(TPL).length, XTPL:Object.keys(XTPL).length, PTPL:Object.keys(PTPL).length, XBLANK:Object.keys(XBLANK).length});
 console.log(rows.join("\n"));
 console.log(`\n==> ${ok}/${COUNTRIES.length} generated a valid non-empty file`);
 console.log("LEAKWORDS check runs separately via pdftotext");
})();
