#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parent
ci = root / 'ci_build.sh'
builder = root / 'build_package.py'

s = ci.read_text(encoding='utf-8')
s = s.replace(
    "cp 'assets_raw/kenney_full/License.txt' assets_raw/kenney/Kenney_License.txt",
    "cp 'assets_raw/kenney_full/License.txt' assets_raw/kenney/Kenney_License.txt\ncp 'assets_raw/kenney_full/Models/GLB format/Textures/colormap.png' assets_raw/kenney/colormap.png",
    1,
)
s = s.replace(
    "'--use-angle=swiftshader','--window-size=1920,1080'",
    "'--use-angle=swiftshader','--enable-unsafe-swiftshader','--window-size=1600,900'",
    1,
)
s = s.replace(
    "const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});",
    "const page=await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:1});page.setDefaultTimeout(120000);",
    1,
)
s = s.replace(
    "await page.waitForFunction(()=>window.__TGD_READY===true,{timeout:180000});",
    "await page.waitForFunction(()=>window.__TGD_READY===true,null,{timeout:180000});",
    1,
)
s = s.replace("await page.waitForTimeout(2500);", "await page.waitForTimeout(5000);", 1)
s = s.replace(
    "await page.screenshot({path:'validation/offline_runtime_1920x1080.png',fullPage:true});",
    "await page.screenshot({path:'validation/offline_runtime_1600x900.png',fullPage:true,timeout:120000});",
    1,
)
s = s.replace(
    "if(logs.some(x=>x.includes('[pageerror]')))throw new Error('Page errors detected: '+logs.join('\\n'));",
    "if(logs.some(x=>x.includes('[pageerror]')||x.includes('[error]')))throw new Error('Browser errors detected: '+logs.join('\\n'));",
    1,
)
ci.write_text(s, encoding='utf-8')

b = builder.read_text(encoding='utf-8')
b = b.replace(
    '"linerSmall": b64_data(RAW / "kenney" / "ship-ocean-liner-small.glb", "model/gltf-binary"),',
    '"linerSmall": b64_data(RAW / "kenney" / "ship-ocean-liner-small.glb", "model/gltf-binary"),\n            "colormap": b64_data(RAW / "kenney" / "colormap.png", "image/png"),',
    1,
)
b = b.replace(
    "async function loadOfflinePremiumAssets(){\n  setLoad(88,'加载离线 HDRI、PBR 材质与高质量船舶模型');",
    "async function loadOfflinePremiumAssets(){\n  THREE.DefaultLoadingManager.setURLModifier(url=>url.includes('Textures/colormap.png')?OFFLINE_ASSETS.kenney.colormap:url);\n  setLoad(88,'加载离线 HDRI、PBR 材质与高质量船舶模型');",
    1,
)
builder.write_text(b, encoding='utf-8')

checks = {
    'ci_has_colormap_copy': 'assets_raw/kenney/colormap.png' in s,
    'ci_has_screenshot_timeout': 'timeout:120000' in s,
    'ci_checks_console_errors': "x.includes('[error]')" in s,
    'builder_embeds_colormap': 'OFFLINE_ASSETS.kenney.colormap' in b and '"colormap": b64_data' in b,
}
print(checks)
if not all(checks.values()):
    raise SystemExit('Final patch did not apply completely')
