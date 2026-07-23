#!/usr/bin/env python3
from __future__ import annotations

import datetime
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "dist" / "Three_Gorges_Offline_Premium"
ZIP = ROOT / "dist" / "Three_Gorges_Offline_Premium_Package_v1.2.zip"


def patch_runtime() -> None:
    app = PKG / "app.bundle.js"
    s = app.read_text(encoding="utf-8")

    start = s.index("function iT(")
    end = s.index("var Q2=[]", start)
    material = '''function iT(Z=481904,A=5155765,V=.9){let l=new pA(Z).lerp(new pA(A),.58),W=new uV({color:l,transparent:!1,opacity:1,depthWrite:!0,depthTest:!0,side:Nl,fog:!0,toneMapped:!1,polygonOffset:!0,polygonOffsetFactor:-3,polygonOffsetUnits:-4});return W.uniforms={uTime:{value:0},uDeep:{value:new pA(Z)},uShallow:{value:new pA(A)},uOpacity:{value:1}},W.userData.robustWater=!0,W.userData.unlitBase=!0,W}'''
    s = s[:start] + material + s[end:]

    start = s.index("function z2(")
    end = s.index("var xh=", start)
    surface = '''function z2(Z,A,V,l=!0){let d=[],U=[],p=[];for(let e=0;e<=320;e++){let t=e/320,S=fV(Z,A,t),J=zZ(S),N=TW(S)*(l?1.24:1.08);for(let k=0;k<=10;k++){let T=k/10;d.push(S,0,J+(T-.5)*N),U.push(t,T)}}for(let e=0;e<320;e++)for(let t=0;t<10;t++){let S=e*11+t,J=S+11;p.push(S,J,S+1,J,J+1,S+1)}let n=new mV;n.setAttribute("position",new DA(d,3)),n.setAttribute("uv",new DA(U,2)),n.setIndex(p),n.computeVertexNormals(),n.computeBoundingSphere();let m=iT(l?481904:746872,l?5155765:5353405,.9);Q2.push(m);let h=new bA(n,m);h.position.y=V+.65,h.renderOrder=12,h.frustumCulled=!1,h.userData.waterBase={upstream:l,x0:Z,x1:A,guaranteedVisible:!0};let e=new gV({color:l?5684457:6147316,roughness:.055,metalness:.04,clearcoat:1,clearcoatRoughness:.02,reflectivity:.92,envMapIntensity:2.1,transparent:!0,opacity:.34,depthWrite:!1,depthTest:!0,side:Nl,polygonOffset:!0,polygonOffsetFactor:-4,polygonOffsetUnits:-5,emissive:l?481904:746872,emissiveIntensity:.018}),t=new bA(n,e);return t.position.y=.22,t.renderOrder=13,t.frustumCulled=!1,h.add(t),h.userData.surfaceGlaze=t,HU.add(h),h}'''
    s = s[:start] + surface + s[end:]

    s = s.replace("function Rm(){xh.position.y=WA.level;", "function Rm(){xh.position.y=WA.level+.65;", 1)
    s = s.replace("function Rm(){xh.position.y=WA.level-.35;", "function Rm(){xh.position.y=WA.level+.65;", 1)
    s = s.replace("U=TW(a)*1.05*Z;", "U=TW(a)*1.24*Z;", 1)
    s = s.replace("U=TW(a)*1.12*Z;", "U=TW(a)*1.24*Z;", 1)

    old_candidates = [
        "for(let d of Q2)d.uniforms.uTime.value=V;",
        "for(let d of Q2)d.uniforms.uTime.value=V,d.roughness=.155+.018*Math.sin(V*.55);for(let d of [xh,qG]){let U=d.userData.surfaceGlaze;U&&(U.material.opacity=.255+.045*Math.sin(V*.72+(d===qG?1.35:0)),U.position.y=.5+.045*Math.sin(V*.9+(d===qG?.8:0)))};",
    ]
    replacement = "for(let d of Q2)d.uniforms.uTime.value=V;for(let d of [xh,qG]){let U=d.userData.surfaceGlaze;U&&(U.material.opacity=.31+.055*Math.sin(V*.72+(d===qG?1.35:0)),U.position.y=.22+.045*Math.sin(V*.9+(d===qG?.8:0)))};"
    found = False
    for old in old_candidates:
        if old in s:
            s = s.replace(old, replacement, 1)
            found = True
            break
    if not found:
        raise RuntimeError("water animation marker not found")

    marker = "var xh=z2(-kV.worldW/2,-68,WA.level,!0),qG=z2(82,kV.worldW/2,kV.tailBase,!1);"
    if marker not in s:
        raise RuntimeError("water construction marker not found")
    s = s.replace(
        marker,
        marker + "window.__TGD_WATER_DIAGNOSTICS={upstream:xh,downstream:qG,materials:Q2,scene:Tl,camera:BZ,renderer:rV,composer:_W,mode:\"unlit-opaque-base-plus-pbr-glaze\"};",
        1,
    )

    if "I2<24" in s or "lastFps<24" in s:
        raise RuntimeError("automatic quality downgrade remains in runtime")
    if "uniform vec3 uDeep;uniform vec3 uShallow" in s:
        raise RuntimeError("legacy custom water shader remains")

    app.write_text(s, encoding="utf-8")


def update_docs() -> None:
    validation = PKG / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    note = validation / "WATER_SURFACE_FIX_v1.2_STRONG.txt"
    note.write_text(
        "三峡水面强制可见兼容修复（v1.2）\n\n"
        "本版不再把主江面可见性建立在透明Shader或场景灯光之上。主水层使用不受光照影响的完全不透明 MeshBasicMaterial，置于工程水位以上0.65 m，并关闭超长河带的视锥剔除；其上叠加透明 MeshPhysicalMaterial 高光层，用于反射、清漆高光和轻微动态波光。\n\n"
        "即使透明混合、HDRI、PBR光照或部分显卡驱动出现兼容问题，不透明基础水层仍应保持清晰可见。上游和下游水带均适当加宽，避免真实DEM与程序化河槽边缘覆盖江面。高画质保持锁定，未恢复任何低帧率自动降画质逻辑。\n",
        encoding="utf-8",
    )
    for name in ["README_FIRST.txt", "README_使用说明.md"]:
        p = PKG / name
        if not p.exists():
            continue
        p.write_text(
            p.read_text(encoding="utf-8", errors="replace")
            + "\n\n【v1.2 水面强制可见修复】主水层为不透明、无光照依赖的基础层，上方叠加PBR高光层；水面整体上抬0.65 m并加宽，不再依赖透明Shader。\n",
            encoding="utf-8",
        )

    mp = PKG / "PACKAGE_MANIFEST.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    except Exception:
        manifest = {}
    manifest.update(
        {
            "version": "1.2-strong-water",
            "water_rendering": "opaque_unlit_base_plus_pbr_glaze",
            "water_base": "opaque MeshBasicMaterial, toneMapped=false",
            "water_base_elevation_offset_m": 0.65,
            "water_glaze": "transparent MeshPhysicalMaterial",
            "custom_water_shader_required": False,
            "auto_quality_downgrade_removed": True,
            "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def checksums() -> None:
    validation = PKG / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and p.name not in {"SHA256SUMS_ALL.txt", "SHA256SUMS_CORE.txt"}:
            rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}")
    (validation / "SHA256SUMS_ALL.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    core = []
    for name in ["index.html", "OPEN_ME.html", "双击打开_三峡水利枢纽离线演示.html", "app.bundle.js", "PACKAGE_MANIFEST.json"]:
        p = PKG / name
        if p.exists():
            core.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    (validation / "SHA256SUMS_CORE.txt").write_text("\n".join(core) + "\n", encoding="utf-8")


def pack() -> None:
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, strict_timestamps=False) as z:
        for p in sorted(PKG.rglob("*")):
            if p.is_file():
                z.write(p, (Path(PKG.name) / p.relative_to(PKG)).as_posix())
    print(json.dumps({"zip": str(ZIP), "size": ZIP.stat().st_size, "sha256": hashlib.sha256(ZIP.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    if not PKG.exists():
        raise SystemExit(f"package directory not found: {PKG}")
    patch_runtime()
    update_docs()
    checksums()
    pack()
