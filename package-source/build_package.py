#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import mimetypes
import os
import re
import shutil
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source_original.html"
RAW = ROOT / "assets_raw"
OUT = ROOT / "dist" / "Three_Gorges_Offline_Premium"


def b64_data(path: Path, mime: str | None = None) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    if mime is None:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def text_data(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def embed_gltf(gltf_path: Path) -> str:
    """Return a glTF JSON data URI with referenced local binary/images embedded."""
    doc = json.loads(gltf_path.read_text(encoding="utf-8"))
    for buf in doc.get("buffers", []):
        uri = buf.get("uri")
        if uri and not uri.startswith("data:"):
            p = gltf_path.parent / uri
            buf["uri"] = b64_data(p, "application/octet-stream")
    for image in doc.get("images", []):
        uri = image.get("uri")
        if uri and not uri.startswith("data:"):
            p = gltf_path.parent / uri
            image["uri"] = b64_data(p)
    packed = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "data:model/gltf+json;base64," + base64.b64encode(packed).decode("ascii")


def write_assets_module() -> Path:
    a = {
        "polyHaven": {
            "hdr": b64_data(RAW / "polyhaven" / "dam_wall_2k.hdr", "application/octet-stream"),
            "concrete": {
                "color": b64_data(RAW / "polyhaven" / "concrete_diff_2k.jpg", "image/jpeg"),
                "normal": b64_data(RAW / "polyhaven" / "concrete_nor_gl_2k.jpg", "image/jpeg"),
                "roughness": b64_data(RAW / "polyhaven" / "concrete_rough_2k.jpg", "image/jpeg"),
                "displacement": b64_data(RAW / "polyhaven" / "concrete_disp_2k.jpg", "image/jpeg"),
            },
            "rock": embed_gltf(RAW / "polyhaven" / "rock_07_1k.gltf"),
        },
        "ambientCG": {
            "concrete007": {
                "color": b64_data(RAW / "ambientcg" / "Concrete007_1K-JPG_Color.jpg", "image/jpeg"),
                "normal": b64_data(RAW / "ambientcg" / "Concrete007_1K-JPG_NormalGL.jpg", "image/jpeg"),
                "roughness": b64_data(RAW / "ambientcg" / "Concrete007_1K-JPG_Roughness.jpg", "image/jpeg"),
                "ao": b64_data(RAW / "ambientcg" / "Concrete007_1K-JPG_AmbientOcclusion.jpg", "image/jpeg"),
                "displacement": b64_data(RAW / "ambientcg" / "Concrete007_1K-JPG_Displacement.jpg", "image/jpeg"),
            }
        },
        "kenney": {
            "cargo": b64_data(RAW / "kenney" / "ship-cargo-a.glb", "model/gltf-binary"),
            "large": b64_data(RAW / "kenney" / "ship-large.glb", "model/gltf-binary"),
            "liner": b64_data(RAW / "kenney" / "ship-ocean-liner.glb", "model/gltf-binary"),
            "linerSmall": b64_data(RAW / "kenney" / "ship-ocean-liner-small.glb", "model/gltf-binary"),
        },
        "quaternius": {
            "cruiseObj": text_data(RAW / "quaternius" / "CruiseShip.obj"),
            "cruiseMtl": text_data(RAW / "quaternius" / "CruiseShip.mtl"),
            "sailObj": text_data(RAW / "quaternius" / "Sail_ship.obj"),
            "sailMtl": text_data(RAW / "quaternius" / "Sail_ship.mtl"),
        },
        "terrain": b64_data(RAW / "terrain" / "three_gorges_terrarium_3x3.png", "image/png"),
    }
    path = ROOT / "assets.generated.js"
    path.write_text("export const OFFLINE_ASSETS=" + json.dumps(a, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    return path


PREMIUM_JS = r'''
const premiumShoals=[];

function dataUriToArrayBuffer(uri){
  const comma=uri.indexOf(','),meta=uri.slice(0,comma),data=uri.slice(comma+1);
  if(meta.includes(';base64')){const bin=atob(data),arr=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);return arr.buffer}
  return new TextEncoder().encode(decodeURIComponent(data)).buffer;
}
function configureMap(tex,{color=false,rx=6,ry=3}={}){
  if(color)tex.colorSpace=THREE.SRGBColorSpace;
  tex.wrapS=tex.wrapT=THREE.RepeatWrapping;tex.repeat.set(rx,ry);tex.anisotropy=Math.min(16,renderer.capabilities.getMaxAnisotropy());tex.needsUpdate=true;return tex;
}
function loadTextureData(uri,opts){return new Promise((resolve,reject)=>new THREE.TextureLoader().load(uri,t=>resolve(configureMap(t,opts)),undefined,reject));}
function parseGLB(uri){return new Promise((resolve,reject)=>new GLTFLoader().parse(dataUriToArrayBuffer(uri),'',resolve,reject));}
function parseEmbeddedGLTF(uri){const comma=uri.indexOf(','),text=decodeURIComponent(escape(atob(uri.slice(comma+1))));return new Promise((resolve,reject)=>new GLTFLoader().parse(text,'',resolve,reject));}
function cloneStatic(root){const c=root.clone(true);c.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(Array.isArray(o.material))o.material=o.material.map(m=>m.clone());else if(o.material)o.material=o.material.clone();}});return c;}
function orientAndFit(root,targetLength,targetWidth,{draft=0.20,heading=0}={}){
  const holder=new THREE.Group();holder.add(root);root.updateMatrixWorld(true);
  let box=new THREE.Box3().setFromObject(root),size=box.getSize(new THREE.Vector3());
  if(size.z>size.x*1.12){root.rotation.y+=Math.PI/2;root.updateMatrixWorld(true);box=new THREE.Box3().setFromObject(root);size=box.getSize(new THREE.Vector3());}
  const scale=Math.min(targetLength/Math.max(size.x,.001),(targetWidth*1.08)/Math.max(size.z,.001));root.scale.multiplyScalar(scale);root.updateMatrixWorld(true);
  box=new THREE.Box3().setFromObject(root);const center=box.getCenter(new THREE.Vector3());const scaled=box.getSize(new THREE.Vector3());
  root.position.x-=center.x;root.position.z-=center.z;root.position.y-=box.min.y;root.position.y-=Math.max(2,targetWidth*draft);
  holder.rotation.y=heading;holder.userData.premiumAsset=true;holder.userData.actualLength=scaled.x;return holder;
}
function replaceShipGeometry(group,source,targetLength,targetWidth,opts={}){
  if(!group||!source)return;
  for(const child of [...group.children])if(child.isMesh||child.isGroup)group.remove(child);
  const fitted=orientAndFit(cloneStatic(source),targetLength,targetWidth,opts);group.add(fitted);group.userData.premiumAsset=true;
}
function setMaterialMaps(materials,maps){
  for(const m of materials){m.map=maps.color;m.normalMap=maps.normal;m.roughnessMap=maps.roughness;m.aoMap=maps.ao||null;m.normalScale?.set(.45,.45);m.roughness=.9;m.metalness=.02;m.needsUpdate=true;}
}
function setRootOpacity(root,opacity){root.traverse(o=>{if(o.isMesh&&o.material){const mats=Array.isArray(o.material)?o.material:[o.material];for(const m of mats){m.transparent=true;m.opacity=opacity;m.depthWrite=opacity>.25;m.needsUpdate=true;}}});root.visible=opacity>.08;}

async function loadOfflinePremiumAssets(){
  setLoad(88,'加载离线 HDRI、PBR 材质与高质量船舶模型');
  const result={ok:[],failed:[]};
  const safe=async(name,fn)=>{try{const v=await fn();result.ok.push(name);return v}catch(e){console.warn(name,e);result.failed.push(name);return null}};

  const hdr=await safe('Poly Haven Dam Wall 2K HDRI',()=>new RGBELoader().loadAsync(OFFLINE_ASSETS.polyHaven.hdr));
  if(hdr){hdr.mapping=THREE.EquirectangularReflectionMapping;scene.environment=hdr;scene.environmentIntensity=.72;}

  const ph=await safe('Poly Haven Concrete 2K PBR',async()=>({
    color:await loadTextureData(OFFLINE_ASSETS.polyHaven.concrete.color,{color:true,rx:7,ry:2.5}),
    normal:await loadTextureData(OFFLINE_ASSETS.polyHaven.concrete.normal,{rx:7,ry:2.5}),
    roughness:await loadTextureData(OFFLINE_ASSETS.polyHaven.concrete.roughness,{rx:7,ry:2.5})
  }));
  if(ph)setMaterialMaps([MAT.concrete,MAT.concreteLight],ph);

  const ac=await safe('ambientCG Concrete007 PBR',async()=>({
    color:await loadTextureData(OFFLINE_ASSETS.ambientCG.concrete007.color,{color:true,rx:5,ry:3}),
    normal:await loadTextureData(OFFLINE_ASSETS.ambientCG.concrete007.normal,{rx:5,ry:3}),
    roughness:await loadTextureData(OFFLINE_ASSETS.ambientCG.concrete007.roughness,{rx:5,ry:3}),
    ao:await loadTextureData(OFFLINE_ASSETS.ambientCG.concrete007.ao,{rx:5,ry:3})
  }));
  if(ac)setMaterialMaps([MAT.concreteDark],ac);

  const [cargoGltf,largeGltf,linerGltf,linerSmallGltf]=await Promise.all([
    safe('Kenney Cargo Ship',()=>parseGLB(OFFLINE_ASSETS.kenney.cargo)),
    safe('Kenney Large Ship',()=>parseGLB(OFFLINE_ASSETS.kenney.large)),
    safe('Kenney Ocean Liner',()=>parseGLB(OFFLINE_ASSETS.kenney.liner)),
    safe('Kenney Small Ocean Liner',()=>parseGLB(OFFLINE_ASSETS.kenney.linerSmall))
  ]);
  const cargo=cargoGltf?.scene,large=largeGltf?.scene,liner=linerGltf?.scene,linerSmall=linerSmallGltf?.scene;

  const quatCruise=await safe('Quaternius CruiseShip',async()=>{const mats=new MTLLoader().parse(OFFLINE_ASSETS.quaternius.cruiseMtl,'');mats.preload();return new OBJLoader().setMaterials(mats).parse(OFFLINE_ASSETS.quaternius.cruiseObj)});
  const quatSail=await safe('Quaternius Sail Ship',async()=>{const mats=new MTLLoader().parse(OFFLINE_ASSETS.quaternius.sailMtl,'');mats.preload();return new OBJLoader().setMaterials(mats).parse(OFFLINE_ASSETS.quaternius.sailObj)});

  const models=[cargo,large,liner,quatCruise,linerSmall,quatSail].filter(Boolean);
  anim.navShips.forEach((item,i)=>{const src=models[i%models.length];if(src)replaceShipGeometry(item.ship,src,item.ship.userData.targetLength||170,item.ship.userData.targetWidth||27,{draft:.17});});
  anim.lockLines.forEach((line,i)=>{const src=i?large:cargo;if(src)replaceShipGeometry(line.ship,src,line.ship.userData.targetLength||205,line.ship.userData.targetWidth||30,{draft:.16});});
  if(anim.lift?.ship){const src=quatCruise||linerSmall||liner;if(src)replaceShipGeometry(anim.lift.ship,src,84,14,{draft:.12});}

  const rockGltf=await safe('Poly Haven Rock 07 glTF',()=>parseEmbeddedGLTF(OFFLINE_ASSETS.polyHaven.rock));
  if(rockGltf){
    for(let i=0;i<12;i++){const x=-1800-rng()*7900,z=riverCenterZ(x)+(rng()-.5)*riverWidth(x)*.52,top=147+rng()*23,r=9+rng()*22;const root=orientAndFit(cloneStatic(rockGltf.scene),r*2.6,r*2.1,{draft:0});root.position.set(x,top-r*.45,z);root.rotation.set(rng()*1.2,rng()*Math.PI*2,rng()*.7);navGroup.add(root);premiumShoals.push({root,top});}
  }
  window.__TGD_PREMIUM_ASSETS={loaded:result.ok,failed:result.failed};
  const status=document.getElementById('terrainStatus');if(status)status.textContent=(status.textContent||'离线 DEM')+' · CC0 PBR/模型';
  toast(result.failed.length?`高质量离线素材已加载 ${result.ok.length} 项，${result.failed.length} 项使用程序化兜底`:`高质量离线素材全部加载完成（${result.ok.length} 项）`);
  return result;
}
'''

OFFLINE_TERRAIN = r'''
async function loadTerrainTiles(){const z=12,n=2**z;const lon2x=lon=>(lon+180)/360*n;const lat2y=lat=>(1-Math.log(Math.tan(lat*Math.PI/180)+1/Math.cos(lat*Math.PI/180))/Math.PI)/2*n;const cx=Math.floor(lon2x(DATA.lon)),cy=Math.floor(lat2y(DATA.lat)),minX=cx-1,minY=cy-1,size=256,canvas=document.createElement('canvas');canvas.width=canvas.height=size*3;const ctx=canvas.getContext('2d',{willReadFrequently:true});
  const tileImage=await new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=OFFLINE_ASSETS.terrain});ctx.drawImage(tileImage,0,0,canvas.width,canvas.height);$('#terrainStatus').textContent='离线真实高程 9/9';setLoad(84,'离线 Mapzen Terrarium 高程已载入');
  const img=ctx.getImageData(0,0,canvas.width,canvas.height).data;const cos=Math.cos(DATA.lat*Math.PI/180);
  for(let i=0;i<tp.count;i++){const x=tp.getX(i),zWorld=tp.getZ(i),lon=DATA.lon+x/(111320*cos),lat=DATA.lat+zWorld/111320;const px=(lon2x(lon)-minX)*size,py=(lat2y(lat)-minY)*size;const ix=clamp(Math.floor(px),0,canvas.width-1),iy=clamp(Math.floor(py),0,canvas.height-1),k=(iy*canvas.width+ix)*4;let h=img[k]*256+img[k+1]+img[k+2]/256-32768;h=carveEngineering(x,zWorld,h);tp.setY(i,h);terrainHeights[i]=h;const c=terrainColor(h,x,zWorld);colors[i*3]=c.r;colors[i*3+1]=c.g;colors[i*3+2]=c.b}
  tp.needsUpdate=true;terrainGeo.attributes.color.needsUpdate=true;terrainGeo.computeVertexNormals();terrainGeo.attributes.normal.needsUpdate=true;state.terrainReady=true;$('#terrainStatus').textContent='离线 Mapzen 开放高程';$('#tRender').firstChild.textContent='离线开放 DEM';
  for(let i=0;i<treeXZ.length;i++){const [x,zWorld,s]=treeXZ[i];dummy.position.set(x,getTerrainHeight(x,zWorld)+9*s,zWorld);dummy.scale.set(s,s,s);dummy.rotation.y=(i*.618)%Math.PI;dummy.updateMatrix();trees.setMatrixAt(i,dummy.matrix)}trees.instanceMatrix.needsUpdate=true;
  toast('离线开放高程加载完成：无需网络或本地服务器');
}
const terrainLoadPromise=loadTerrainTiles().catch(err=>{$('#terrainStatus').textContent='程序化地形（离线兜底）';console.warn('Embedded terrain unavailable',err);toast('离线高程图无法解析，已保留程序化峡谷地形')});
'''


def patch_js(js: str) -> str:
    imports = """import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';
import { OFFLINE_ASSETS } from './assets.generated.js';"""
    js = re.sub(r"import \* as THREE from 'three';.*?import \{ RoomEnvironment \} from 'three/addons/environments/RoomEnvironment\.js';", imports, js, count=1, flags=re.S)

    js = js.replace("function createCargoShip(length=180,width=28,color=0x225a75,containers=true){const g=new THREE.Group();g.userData.waterline=0;",
                    "function createCargoShip(length=180,width=28,color=0x225a75,containers=true){const g=new THREE.Group();g.userData.waterline=0;g.userData.targetLength=length;g.userData.targetWidth=width;")

    marker = "const terrainGroup=new THREE.Group()"
    if marker not in js:
        raise RuntimeError("MAT insertion marker not found")
    js = js.replace(marker, PREMIUM_JS + "\n" + marker, 1)

    terrain_pattern = re.compile(r"async function loadTerrainTiles\(\)\{.*?\n\}\nloadTerrainTiles\(\)\.catch\(err=>\{.*?\}\);", re.S)
    js, n = terrain_pattern.subn(OFFLINE_TERRAIN.strip(), js, count=1)
    if n != 1:
        raise RuntimeError(f"terrain replacement failed: {n}")

    auto = "if(state.quality==='high'&&lastFps<24){setQuality('medium');$('#quality').value='medium';toast('检测到帧率较低，已自动切换为中画质')}"
    if auto not in js:
        raise RuntimeError("auto downgrade block not found")
    js = js.replace(auto, "", 1)

    old_quality = "function setQuality(q){state.quality=q;const dpr=q==='high'?Math.min(devicePixelRatio,2):q==='medium'?Math.min(devicePixelRatio,1.35):1;renderer.setPixelRatio(dpr);composer.setPixelRatio(dpr);renderer.shadowMap.enabled=q!=='low';sun.castShadow=q==='high';bloom.enabled=q!=='low';trees.visible=q!=='low';toast(`画质已切换：${q==='high'?'高画质':q==='medium'?'中画质':'流畅优先'}`)}"
    new_quality = "function setQuality(q){state.quality=q;const dpr=q==='high'?Math.min(devicePixelRatio,2):q==='medium'?Math.min(devicePixelRatio,1.35):1;renderer.setPixelRatio(dpr);composer.setPixelRatio(dpr);renderer.shadowMap.enabled=q!=='low';sun.castShadow=q==='high';bloom.enabled=q!=='low';trees.visible=q!=='low';toast(`画质已切换：${q==='high'?'高画质（锁定，不自动降级）':q==='medium'?'中画质':'流畅优先'}`)}"
    js = js.replace(old_quality, new_quality, 1)

    shoal_line = "for(const s of anim.shoals){const sub=state.level-s.top;s.mesh.material.opacity=sub>5?.06:sub>0?lerp(.78,.12,sub/5):1;s.mesh.visible=s.mesh.material.opacity>.08}"
    js = js.replace(shoal_line, shoal_line + "for(const s of premiumShoals){const sub=state.level-s.top;const opacity=sub>5?.05:sub>0?lerp(.82,.1,sub/5):1;setRootOpacity(s.root,opacity)}", 1)

    old_boot = "setDay('day');syncControls();updateWaterGeometry();window.__TGD_READY=true;setLoad(100,'场景就绪');\nsetTimeout(()=>{const l=$('#loading');l.style.opacity='0';setTimeout(()=>l.remove(),800);openInfo(damPick.userData.info);animate(performance.now())},700);"
    new_boot = """async function bootOfflinePremium(){
  setDay('day');syncControls();updateWaterGeometry();
  await Promise.allSettled([terrainLoadPromise,loadOfflinePremiumAssets()]);
  setQuality('high');$('#quality').value='high';window.__TGD_READY=true;setLoad(100,'离线高质量场景就绪');
  setTimeout(()=>{const l=$('#loading');l.style.opacity='0';setTimeout(()=>l.remove(),800);openInfo(damPick.userData.info);animate(performance.now())},450);
}
bootOfflinePremium().catch(err=>{console.error(err);window.__TGD_READY=true;setLoad(100,'场景已启用程序化兜底');setTimeout(()=>{const l=$('#loading');if(l){l.style.opacity='0';setTimeout(()=>l.remove(),800)}openInfo(damPick.userData.info);animate(performance.now())},450)});"""
    if old_boot not in js:
        raise RuntimeError("boot block not found")
    js = js.replace(old_boot, new_boot, 1)
    return js


def patch_html(html: str, module_js: str) -> tuple[str, str]:
    html = re.sub(r'<script type="importmap">.*?</script>\s*', '', html, count=1, flags=re.S)
    html = html.replace("if(status)status.innerHTML='三维模块加载超时。请确认网络可访问 Three.js CDN，并通过本地静态服务器运行。';",
                        "if(status)status.innerHTML='离线三维引擎初始化时间较长。请确认浏览器支持 WebGL2 并已启用硬件加速；无需安装 Python 或启动本地服务器。';")
    html = html.replace("},12000);", "},30000);", 1)
    html = html.replace('<option value="high">高画质</option>', '<option value="high">高画质（锁定）</option>')
    html, count = re.subn(r'<script type="module">.*?</script>', '<script src="app.bundle.js"></script>', html, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"module script replacement failed: {count}")
    html = html.replace('Three.js', 'Three.js · 离线 CC0 高质量素材版', 1)
    return html, module_js


def main() -> None:
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    html = SRC.read_text(encoding="utf-8")
    match = re.search(r'<script type="module">\s*(.*?)\s*</script>', html, re.S)
    if not match: raise RuntimeError("module script not found")
    original_module = match.group(1)
    patched = patch_js(original_module)
    patched_html, _ = patch_html(html, original_module)
    (ROOT / "entry.js").write_text(patched, encoding="utf-8")
    write_assets_module()
    (ROOT / "index.template.html").write_text(patched_html, encoding="utf-8")

    # Files copied after esbuild runs in workflow.
    meta = {
        "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "auto_quality_downgrade_removed": True,
        "default_quality": "high",
        "offline_assets_embedded": True,
    }
    (ROOT / "build_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
