import React from "react";
import { Composition } from "remotion";
import { CampusGuide, TOTAL_FRAMES } from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="CampusGuide"
    component={CampusGuide}
    durationInFrames={TOTAL_FRAMES}
    fps={30}
    width={1920}
    height={1080}
  />
);
