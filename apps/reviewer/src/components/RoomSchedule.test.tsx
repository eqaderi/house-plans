import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { HouseModel, EvaluationReport } from "../types/schemas";
import { RoomSchedule } from "./RoomSchedule";

const model = {
  spaces: [{ id: "room", name: "Room", level_id: "ground", function: "bedroom",
    boundary: { outer: [[0,0], [4,0], [4,3], [0,3]], holes: [] } }],
} as unknown as HouseModel;

describe("RoomSchedule net areas", () => {
  it("shows independently measured 4x3m partition-room area with gross basis", () => {
    const evaluation = { metrics: [
      { evaluator: "NetAreaEvaluator", metric: "net_area_m2", status: "measured",
        subject_ids: ["room"], value: 10.972 },
      { evaluator: "NetAreaEvaluator", metric: "net_wall_basis_complete", status: "measured",
        subject_ids: ["room"], value: false },
    ] } as EvaluationReport;
    const html = renderToStaticMarkup(<RoomSchedule model={model} evaluation={evaluation} />);
    expect(html).toContain("12.0 m²");
    expect(html).toContain("11.0 m²");
    expect(html).toContain("Total Modelled Net Area: 11.0 m²");
    expect(html).toContain("Incomplete wall model");
  });

  it("keeps absent or unmeasured net values explicit", () => {
    const html = renderToStaticMarkup(<RoomSchedule model={model} />);
    expect(html).toContain("Total Modelled Net Area: not checked");
    const evaluation = { metrics: [{ evaluator: "NetAreaEvaluator", metric: "net_area_m2",
      status: "not_checked", value: null, subject_ids: ["room"] }] } as EvaluationReport;
    expect(renderToStaticMarkup(<RoomSchedule model={model} evaluation={evaluation} />))
      .toContain("Total Modelled Net Area: not checked");
  });

  it("shows an inferred net area from an incomplete wall model with its marker", () => {
    const evaluation = { metrics: [
      { evaluator: "NetAreaEvaluator", metric: "net_area_m2", status: "inferred",
        subject_ids: ["room"], value: 11.4 },
      { evaluator: "NetAreaEvaluator", metric: "net_wall_basis_complete", status: "measured",
        subject_ids: ["room"], value: false },
    ] } as EvaluationReport;
    const html = renderToStaticMarkup(<RoomSchedule model={model} evaluation={evaluation} />);
    expect(html).toContain("11.4 m² *");
  });

  it("renders a boundary without a holes array", () => {
    const bare = { spaces: [{ ...model.spaces![0], boundary: { outer: [[0,0], [4,0], [4,3], [0,3]] } }] } as unknown as HouseModel;
    expect(renderToStaticMarkup(<RoomSchedule model={bare} />)).toContain("12.0 m²");
  });
});
