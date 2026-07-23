import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const root=path.resolve('package-source/dist/Three_Gorges_Offline_Premium');
const out=path.join(root,'validation');
fs.mkdirSync(out,{recursive:true});
const candidates=['/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium-browser','/usr/bin/chromium'];
const executablePath=candidates.find(fs.existsSync);
if(!executablePath)throw new Error('Chrome/Chromium not found');

const logs=[];
const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox','--disable-dev-shm-usage','--ignore-gpu-blocklist','--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader','--window-size=1600,900']});
const page=await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:1});
page.setDefaultTimeout(240000);
page.on('console',m=>logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror',e=>logs.push(`[pageerror] ${e.stack||e}`));
await page.goto(pathToFileURL(path.join(root,'index.html')).href,{waitUntil:'load',timeout:240000});
await page.waitForFunction(()=>window.__TGD_READY===true,null,{timeout:240000});
await page.waitForTimeout(6000);

const report=await page.evaluate(()=>{
  const t=window.__TGD_WATER_DIAGNOSTICS;
  if(!t)throw new Error('water diagnostics handle missing');
  const up=t.upstream,down=t.downstream;
  const snapshot=()=>{
    t.composer.render();
    const src=t.renderer.domElement;
    const c=document.createElement('canvas');c.width=src.width;c.height=src.height;
    const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(src,0,0);
    return ctx.getImageData(0,0,c.width,c.height);
  };
  up.visible=true;down.visible=true;
  const on=snapshot();
  up.visible=false;down.visible=false;
  const off=snapshot();
  up.visible=true;down.visible=true;t.composer.render();
  let changed=0,sum=0,max=0,samples=0;
  const stride=4;
  for(let y=0;y<on.height;y+=stride){for(let x=0;x<on.width;x+=stride){
    const i=(y*on.width+x)*4;
    const d=Math.abs(on.data[i]-off.data[i])+Math.abs(on.data[i+1]-off.data[i+1])+Math.abs(on.data[i+2]-off.data[i+2]);
    sum+=d;if(d>18)changed++;if(d>max)max=d;samples++;
  }}
  const info=o=>({
    visible:o.visible,frustumCulled:o.frustumCulled,renderOrder:o.renderOrder,
    position:o.position.toArray(),materialType:o.material.type,transparent:o.material.transparent,
    opacity:o.material.opacity,depthWrite:o.material.depthWrite,depthTest:o.material.depthTest,
    robustWater:o.material.userData?.robustWater===true,
    unlitBase:o.material.userData?.unlitBase===true,
    guaranteedVisible:o.userData.waterBase?.guaranteedVisible===true,
    childCount:o.children.length,
    glazeType:o.userData.surfaceGlaze?.material?.type||null,
    glazeOpacity:o.userData.surfaceGlaze?.material?.opacity??null
  });
  return {
    ready:window.__TGD_READY,
    mode:t.mode,
    premium:window.__TGD_PREMIUM_ASSETS,
    quality:document.querySelector('#quality')?.value,
    terrain:document.querySelector('#terrainStatus')?.textContent,
    upstream:info(up),downstream:info(down),
    visualContribution:{changedPixels:changed,samples,changedRatio:changed/samples,meanRgbDifference:sum/samples,maxRgbDifference:max},
    canvas:{width:on.width,height:on.height}
  };
});

await page.screenshot({path:path.join(out,'water_v12_runtime_1600x900.png'),fullPage:true,timeout:240000});
fs.writeFileSync(path.join(out,'water_v12_runtime_report.json'),JSON.stringify(report,null,2));
fs.writeFileSync(path.join(out,'water_v12_browser_console.log'),logs.join('\n'));
await browser.close();

const failures=[];
if(report.mode!=='unlit-opaque-base-plus-pbr-glaze')failures.push(`unexpected water mode: ${report.mode}`);
for(const [name,w] of Object.entries({upstream:report.upstream,downstream:report.downstream})){
  if(!w.visible)failures.push(`${name} not visible`);
  if(w.materialType!=='MeshBasicMaterial')failures.push(`${name} base is not MeshBasicMaterial`);
  if(w.transparent!==false||w.opacity!==1||w.depthWrite!==true)failures.push(`${name} base is not opaque/depth-writing`);
  if(!w.robustWater||!w.unlitBase||!w.guaranteedVisible)failures.push(`${name} guaranteed-visible flags missing`);
  if(w.childCount<1||w.glazeType!=='MeshPhysicalMaterial')failures.push(`${name} PBR highlight glaze missing`);
  if(w.frustumCulled!==false)failures.push(`${name} frustum culling not disabled`);
}
if(report.quality!=='high')failures.push(`quality is ${report.quality}, expected high`);
if(report.visualContribution.changedRatio<0.002)failures.push(`water visual contribution too small: ${report.visualContribution.changedRatio}`);
if(report.visualContribution.meanRgbDifference<0.20)failures.push(`water mean RGB contribution too small: ${report.visualContribution.meanRgbDifference}`);
if(logs.some(x=>x.includes('[pageerror]')))failures.push('page error detected');
if(failures.length)throw new Error(failures.join('; ')+'\n'+JSON.stringify(report,null,2)+'\n'+logs.join('\n'));
console.log(JSON.stringify(report,null,2));
