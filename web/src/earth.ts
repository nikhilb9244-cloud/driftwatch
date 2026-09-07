import Globe, {type GlobeInstance} from 'globe.gl';

/** The same Earth, textures and controls in the catalogue and the analysis workspace. */
export function createEarth(container: HTMLElement): GlobeInstance {
  return new Globe(container, {rendererConfig: {antialias: true, alpha: false, powerPreference: 'high-performance'}}).globeImageUrl('textures/earth-blue-marble.jpg')
    .bumpImageUrl('textures/earth-topology.png').backgroundImageUrl('textures/night-sky.png')
    .showAtmosphere(true).atmosphereAltitude(0.12).showGraticules(false);
}
