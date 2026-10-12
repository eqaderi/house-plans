# 3D and Unreal Engine: only after the plan is approved

OpenAI's Astra house demo (developers.openai.com/blog/architectural-visualization-with-astra,
Sept 2026) is the reference for "plan to walkable Unreal scene". Its gates
match ours: **"Draw me a floor plan first. We'll validate and evolve it from
there."** The plan was approved before any detailed 3D; the Blender scene was
backed up before every rebuild; geometry was validated in Blender (door
openings, wall connections, sampled walking routes) before export; Unreal came
last. The authors note the checks "weren't a certification" and the plan
"still needs professional review" — our spec checks cover that part.

Never start this before the owner approves a final-stage revision. Unreal is
not installed on these laptops; the export package is built here and opened on
the Unreal machine.

## Route A — semantic, fastest: IFC straight into Unreal (Datasmith)

`out/<name>/model.ifc` → Unreal 5.x with the Datasmith CAD Importer
(docs: dev.epicgames.com, "Importing IFC files into Unreal Engine using
Datasmith"). Every IFC object becomes an Actor nested Site › Building ›
Storey; psets become metadata, so GlobalIds survive for scripting. Materials
arrive plain: replace them in Unreal (Python) with PBR materials. No lights or
cameras come across.

## Route B — the Astra pattern: IFC → Blender (Bonsai) → FBX + manifest

1. Open the IFC in Blender with Bonsai (headless: `blender --background
   --python <script>`). Keep the IFC as the source; anything added in Blender
   only (furniture, plants, lights) is presentation.
2. Back up the .blend before every rebuild.
3. Validate in Blender before export: door openings clear, walls joined,
   walk routes sampled between rooms, normals not flipped (render review).
4. Export FBX of evaluated geometry (modifiers and curves baked) **plus a
   JSON manifest**: part placements, material assignments, lights, cameras,
   door hinge data, IFC GlobalIds. Convert metres to centimetres and fix the
   axis for Unreal; keep trees and repeated furniture as instances.
5. In Unreal, rebuild materials natively (FBX carries little material data),
   light with sun + sky + volumetric fog and Lumen, and test walk routes with
   normal character collision.

Scanned material and vegetation libraries such as Poly Haven are what made
the Astra scene look real.

## Route C — quick look: IfcConvert to GLB

`IfcConvert out/<name>/model.ifc out/<name>/model.glb --center-model
--weld-vertices` (docs.ifcopenshell.org/ifcconvert/usage.html); import the GLB
through Unreal Interchange, or view it in any glTF viewer. Metadata via
IfcConvert's XML output, keyed by GlobalId.

## Avoid for now

USD with embedded MaterialX in UE 5.6–5.7 loses texture bindings (Unreal
forum reports). Twinmotion does not import IFC directly; go through GLB/FBX.
