
/*
 * Optional compatibility bridge.
 * If your existing map creates its Leaflet object under a custom name,
 * set it here before aerovision-enhanced.js runs:
 *
 * window.AeroVisionMap = yourExistingLeafletMap;
 *
 * The main enhancement script already tries window.map, window.aqiMap,
 * window.dashboardMap and window.leafletMap.
 */
window.addEventListener("load", () => {
  if (window.AeroVisionEnhancement && window.AeroVisionMap) {
    window.AeroVisionEnhancement.state.map = window.AeroVisionMap;
    window.AeroVisionEnhancement.attachToExistingLeafletMap();
  }
});
