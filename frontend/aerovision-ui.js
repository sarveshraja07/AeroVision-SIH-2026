// // ============================================================
// // AEROVISION INDIA
// // PRESENTATION UI ENHANCEMENTS
// // ============================================================
// //
// // UI ONLY.
// //
// // This script intentionally does NOT modify:
// // - map prediction logic
// // - selected June date
// // - /api/predict
// // - Earth Engine
// // - XGBoost
// // - CPCB data
// // - AQI calculation
// // - map layers
// //
// // ============================================================

// (function () {

//     "use strict";


//     // ========================================================
//     // PAGE DETECTION
//     // ========================================================

//     var hasLeafletMap =
//         document.getElementById("map") !== null;


//     if (hasLeafletMap) {

//         document.body.classList.add(
//             "av-map-page"
//         );

//     }


//     // ========================================================
//     // READY ANIMATION
//     // ========================================================

//     window.setTimeout(

//         function () {

//             document.body.classList.add(
//                 "av-ui-ready"
//             );

//         },

//         80

//     );


//     // ========================================================
//     // LANDING PAGE
//     // Nothing functional is changed.
//     // ========================================================

//     if (!hasLeafletMap) {

//         console.log(
//             "✨ AeroVision landing UI enhancements active"
//         );

//         return;

//     }


//     // ========================================================
//     // MAP PRESENTATION CONTROLS
//     // ========================================================

//     var controls =
//         document.createElement(
//             "div"
//         );


//     controls.className =
//         "av-ui-controls";


//     // ========================================================
//     // LEFT PANEL BUTTON
//     // ========================================================

//     var leftButton =
//         document.createElement(
//             "button"
//         );


//     leftButton.type =
//         "button";


//     leftButton.className =
//         "av-ui-action";


//     leftButton.title =
//         "Show or hide map layers panel";


//     leftButton.innerHTML =
//         '☰ <span class="av-ui-label">Layers</span>';


//     // ========================================================
//     // RIGHT PANEL BUTTON
//     // ========================================================

//     var rightButton =
//         document.createElement(
//             "button"
//         );


//     rightButton.type =
//         "button";


//     rightButton.className =
//         "av-ui-action";


//     rightButton.title =
//         "Show or hide analysis panel";


//     rightButton.innerHTML =
//         '◫ <span class="av-ui-label">Analysis</span>';


//     // ========================================================
//     // PRESENTATION MODE
//     // ========================================================

//     var presentationButton =
//         document.createElement(
//             "button"
//         );


//     presentationButton.type =
//         "button";


//     presentationButton.className =
//         "av-ui-action";


//     presentationButton.title =
//         "Toggle presentation mode";


//     presentationButton.innerHTML =
//         '◉ <span class="av-ui-label">Present</span>';


//     // ========================================================
//     // FULLSCREEN BUTTON
//     // ========================================================

//     var fullscreenButton =
//         document.createElement(
//             "button"
//         );


//     fullscreenButton.type =
//         "button";


//     fullscreenButton.className =
//         "av-ui-action";


//     fullscreenButton.title =
//         "Toggle fullscreen";


//     fullscreenButton.innerHTML =
//         '⛶ <span class="av-ui-label">Fullscreen</span>';


//     // ========================================================
//     // ADD CONTROLS
//     // ========================================================

//     controls.appendChild(
//         leftButton
//     );


//     controls.appendChild(
//         rightButton
//     );


//     controls.appendChild(
//         presentationButton
//     );


//     controls.appendChild(
//         fullscreenButton
//     );


//     document.body.appendChild(
//         controls
//     );


//     // ========================================================
//     // MAP MODE BADGE
//     // ========================================================

//     var modeBadge =
//         document.createElement(
//             "div"
//         );


//     modeBadge.className =
//         "av-map-mode-badge";


//     modeBadge.textContent =
//         "CLICK INSIDE THE VALIDATED REGION FOR DATE-SPECIFIC AEROVISION PREDICTION";


//     document.body.appendChild(
//         modeBadge
//     );


//     // ========================================================
//     // LEFT PANEL
//     // ========================================================

//     leftButton.addEventListener(

//         "click",

//         function () {

//             document.body.classList.toggle(
//                 "av-hide-left"
//             );


//             if (
//                 typeof map !== "undefined"
//                 &&
//                 map
//             ) {

//                 window.setTimeout(

//                     function () {

//                         map.invalidateSize();

//                     },

//                     320

//                 );

//             }

//         }

//     );


//     // ========================================================
//     // RIGHT PANEL
//     // ========================================================

//     rightButton.addEventListener(

//         "click",

//         function () {

//             document.body.classList.toggle(
//                 "av-hide-right"
//             );


//             if (
//                 typeof map !== "undefined"
//                 &&
//                 map
//             ) {

//                 window.setTimeout(

//                     function () {

//                         map.invalidateSize();

//                     },

//                     320

//                 );

//             }

//         }

//     );


//     // ========================================================
//     // PRESENTATION MODE
//     // ========================================================

//     presentationButton.addEventListener(

//         "click",

//         function () {

//             var enabled =
//                 document.body.classList.toggle(
//                     "av-presentation-mode"
//                 );


//             presentationButton.innerHTML =

//                 enabled

//                 ?

//                 '● <span class="av-ui-label">Exit Present</span>'

//                 :

//                 '◉ <span class="av-ui-label">Present</span>';


//             if (
//                 typeof map !== "undefined"
//                 &&
//                 map
//             ) {

//                 window.setTimeout(

//                     function () {

//                         map.invalidateSize();

//                     },

//                     320

//                 );

//             }

//         }

//     );


//     // ========================================================
//     // FULLSCREEN
//     // ========================================================

//     fullscreenButton.addEventListener(

//         "click",

//         async function () {

//             try {

//                 if (
//                     !document.fullscreenElement
//                 ) {

//                     await document
//                         .documentElement
//                         .requestFullscreen();

//                 }

//                 else {

//                     await document
//                         .exitFullscreen();

//                 }

//             }

//             catch (error) {

//                 console.warn(
//                     "Fullscreen unavailable:",
//                     error
//                 );

//             }

//         }

//     );


//     // ========================================================
//     // FULLSCREEN BUTTON STATE
//     // ========================================================

//     document.addEventListener(

//         "fullscreenchange",

//         function () {

//             fullscreenButton.innerHTML =

//                 document.fullscreenElement

//                 ?

//                 '↙ <span class="av-ui-label">Exit Fullscreen</span>'

//                 :

//                 '⛶ <span class="av-ui-label">Fullscreen</span>';


//             if (
//                 typeof map !== "undefined"
//                 &&
//                 map
//             ) {

//                 window.setTimeout(

//                     function () {

//                         map.invalidateSize();

//                     },

//                     150

//                 );

//             }

//         }

//     );


//     // ========================================================
//     // KEYBOARD PRESENTATION SHORTCUTS
//     // ========================================================
//     //
//     // P = presentation mode
//     // F = fullscreen
//     //
//     // Ignore keyboard shortcuts while typing/selecting.
//     // ========================================================

//     document.addEventListener(

//         "keydown",

//         function (event) {

//             var target =
//                 event.target;


//             var tag =
//                 target
//                 ?
//                 target.tagName
//                 :
//                 "";


//             if (
//                 tag === "INPUT"
//                 ||
//                 tag === "SELECT"
//                 ||
//                 tag === "TEXTAREA"
//             ) {

//                 return;

//             }


//             if (
//                 event.key.toLowerCase() === "p"
//             ) {

//                 presentationButton.click();

//             }


//             if (
//                 event.key.toLowerCase() === "f"
//             ) {

//                 fullscreenButton.click();

//             }

//         }

//     );


//     // ========================================================
//     // PREDICTION MARKER VISUAL FEEDBACK
//     // ========================================================
//     //
//     // We watch for Leaflet prediction marker DOM changes.
//     // This is visual only.
//     // ========================================================

//     var mapElement =
//         document.getElementById(
//             "map"
//         );


//     if (
//         mapElement
//         &&
//         window.MutationObserver
//     ) {

//         var observer =
//             new MutationObserver(

//                 function () {

//                     var predictionPane =
//                         document.querySelector(
//                             ".leaflet-predictionPane-pane"
//                         );


//                     if (
//                         predictionPane
//                     ) {

//                         predictionPane.style.transition =
//                             "filter .25s ease";

//                     }

//                 }

//             );


//         observer.observe(

//             mapElement,

//             {
//                 childList:
//                     true,

//                 subtree:
//                     true
//             }

//         );

//     }


//     console.log(
//         "✨ AeroVision map presentation UI active"
//     );

// })();