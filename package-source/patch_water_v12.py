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
    material = '''function iT(Z=745590,A=4894653,V=.9){let l=new pA(Z).lerp(new pA(A),.34),W=new gV({color:l,roughness:.16,metalness:.06,clearcoat:1,clearcoatRoughness:.075,reflectivity:.78,envMapIntensity:1.55,transparent:!1,opacity:1,depthWrite:!0,depthTest:!0,side:Nl,polygonOffset:!0,polygonOffsetFactor:-1,polygonOffsetUnits:-2,emissive:Z,emissiveIntensity:.018});return W.uniforms={uTime:{value:0},uDeep:{value:new pA(Z)},uShallow:{value:new pA(A)},uOpacity:{value:1}},W.userData.robustWater=!0,W}'''
    s = s[:start] + material + s[end:]

    start = s.index("function z2(")
    end = s.index("var xh=", start)
    surface = '''function z2(Z,A,V,l=!0){let d=[],U=[],p=[];for(let e=0;e<=260;e++){let t=e/260,S=fV(Z,A,t),J=zZ(S),N=TW(S)*(l?1.12:.96);for(let k=0;k<=8;k++){let T=k/8;d.push(S,0,J+(T-.5)*N),U.push(t,T)}}for(let e=0;e<260;e++)for(let t=0;t<8;t++){let S=e*9+t,J=S+9;p.push(S,J,S+1,J,J+1,S+1)}let n=new mV;n.setAttribute("position",new DA(d,3)),n.setAttribute("uv",new DA(U,2)),n.setIndex(p),n.computeVertexNormals(),n.computeBoundingSphere();let m=iT(l?481904:746872,l?5155765:5353405,.9);Q2.push(m);let h=new bA(n,m);h.position.y=V-.35,h.renderOrder=2,h.frustumCulled=!1,h.userData.waterBase={upstream:l,x0:Z,x1:A};let e=new gV({color:l?5155765:5353405,roughness:.045,metalness:.02,clearcoat:1,clearcoatRoughness:.025,reflectivity:.9,envMapIntensity:1.85,transparent:!0,opacity:.28,depthWrite:!1,depthTest:!0,side:Nl,polygonOffset:!0,polygonOffsetFactor:-2,polygonOffsetUnits:-3,emissive:l?481904:746872,emissiveIntensity:.012}),t=new bA(n,e);return t.position.y=.5,t.renderOrder=3,t.frustumCulled=!1,h.add(t),h.userData.surfaceGlaze=t,HU.add(h),h}'''
    s = s[:start] + surface + s[end:]

    s = s.replace("function Rm(){xh.position.y=WA.level;", "function Rm(){xh.position.y=WA.level-.35;", 1)
    s = s.replace("U=TW(a)*1.05*Z;", "U=TW(a)*1.12*Z;", 1)

    old = "for(let d of Q2)d.uniforms.uTime.value=V;"
    new = "for(let d of Q2)d.uniforms.uTime.value=V,d.roughness=.155+.018*Math.sin(V*.55);for(let d of [xh,qG]){let U=d.userData.surfaceGlaze;U&&(U.material.opacity=.255+.045*Math.sin(V*.72+(d===qG?1.35:0)),U.position.y=.5+.045*Math.sin(V*.9+(d===qG?.8:0)))};"
    if old not in s:
        raise RuntimeError("water animation marker not found")
    s = s.replace(old, new, 1)

    marker = "var xh=z2(-kV.worldW/2,-68,WA.level,!0),qG=z2(82,kV.worldW/2,kV.tailBase,!1);"
    if marker not in s:
        raise RuntimeError("water construction marker not found")
    s = s.replace(marker, marker + "window.__TGD_WATER_DIAGNOSTICS={upstream:xh,downstream:qG,materials:Q2,scene:Tl,camera:BZ,renderer:rV,composer:_W};", 1)

    if "I2<24" in s or "lastFps<24" in s:
        raise RuntimeError("automatic quality downgrade remains in runtime")
    if "uniform vec3 uDeep;uniform vec3 uShallow" in s:
        raise RuntimeError("legacy custom water shader remains")

    app.write_text(s, encoding="utf-8")


def update_docs() -> None:
    note = PKG / "validation" / "WATER_SURFACE_FIX_v1.2.txt"
    note.write_text(
        "三峡水面显示修复说明（v1.2 强制可见水面版）\n\n"
        "1.1版只修正了透明Shader的一个潜在问题，但主江面仍完全依赖单层自定义透明Shader；部分WebGL/ANGLE环境中该层仍可能不产生有效颜色贡献。\n\n"
        "v1.2将主江面改为完全不透明的MeshPhysicalMaterial PBR基础水层，并增加独立透明高光层。透明层即使失效，基础水面仍可见。"
        "同时关闭超大河带视锥误剔除，增加稳定水位偏移，并继续锁定高画质、不启用低帧率自动降画质。\n",
        encoding="utf-8",
    )
    for name in ["README_FIRST.txt", "README_使用说明.md"]:
        p = PKG / name
        p.write_text(
            p.read_text(encoding="utf-8", errors="replace")
            + "\n\n【v1.2 水面修复】主江面采用不透明PBR基础层+透明高光层双保险结构，不再依赖单层自定义透明Shader；高画质仍保持锁定。\n",
            encoding="utf-8",
        )

    mp = PKG / "PACKAGE_MANIFEST.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        manifest = {}
    manifest.update(
        {
            "version": "1.2",
            "water_rendering": "dual_layer_robust_pbr",
            "water_base": "opaque MeshPhysicalMaterial",
            "water_glaze": "transparent MeshPhysicalMaterial",
            "custom_water_shader_required": False,
            "auto_quality_downgrade_removed": True,
            "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def checksums() -> None:
    validation = PKG / "validation"
    rows = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and p.name not in {"SHA256SUMS_ALL.txt", "SHA256SUMS_CORE.txt"}:
            rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}")
    (validation / "SHA256SUMS_ALL.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    core = []
    for name in ["index.html", "OPEN_ME.html", "双击打开_三峡水利枢纽离线演示.html", "app.bundle.js", "PACKAGE_MANIFEST.json"]:
        p = PKG / name
        core.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    (validation / "SHA256SUMS_CORE.txt").write_text("\n".join(core) + "\n", encoding="utf-8")


def pack() -> None:
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, strict_timestamps=False) as z:
        for p in sorted(PKG.rglob("*")):
            if p.is_file():
                z.write(p, (PKG.name / p.relative_to(PKG)).as_posix())
    print(json.dumps({"zip": str(ZIP), "size": ZIP.stat().st_size, "sha256": hashlib.sha256(ZIP.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    if not PKG.exists():
        raise SystemExit(f"package directory not found: {PKG}")
    patch_runtime()
    update_docs()
    checksums()
    pack()
