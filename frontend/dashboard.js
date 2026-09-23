// ============================================================
// AEROVISION INDIA
// FULL REACTIVE DASHBOARD
// SMOOTH AQI SURFACE VERSION
// ============================================================

console.log(
    "Loading AeroVision dashboard..."
);


// ============================================================
// MAP PANES
// ============================================================

function ensurePane(
    name,
    zIndex
) {

    if (
        !map.getPane(
            name
        )
    ) {

        map.createPane(
            name
        );

    }


    map.getPane(
        name
    ).style.zIndex =
        String(
            zIndex
        );

}


ensurePane(
    "windPane",
    400
);

ensurePane(
    "aqiSurfacePane",
    425
);

ensurePane(
    "hchoPane",
    450
);

ensurePane(
    "firePane",
    550
);

ensurePane(
    "cpcbPane",
    650
);

ensurePane(
    "predictionPane",
    700
);


[
    "windPane",
    "aqiSurfacePane",
    "hchoPane",
    "firePane",
    "cpcbPane",
    "predictionPane"
]

.forEach(

    function(name) {

        var pane =
            map.getPane(
                name
            );


        if (
            pane
        ) {

            pane.style.pointerEvents =
                "auto";

        }

    }

);


// ============================================================
// LAYERS
// ============================================================

var cpcbLayer =
    L.layerGroup();


var hchoLayer =
    L.layerGroup();


var fireLayer =
    L.layerGroup();


var windLayer =
    L.layerGroup();


var aqiSurfaceLayer =
    L.layerGroup();


var aqiSurfaceInteractiveLayer =
    L.layerGroup();


var aqiSurfaceRaster =
    null;


// ============================================================
// REGISTER
// ============================================================

layerDict[
    "cpcb"
] = cpcbLayer;


layerDict[
    "hcho"
] = hchoLayer;


layerDict[
    "fire"
] = fireLayer;


layerDict[
    "wind"
] = windLayer;


layerDict[
    "aqiSurface"
] = aqiSurfaceLayer;


// ============================================================
// MODEL COVERAGE
// ============================================================

var PROTOTYPE_MIN_LAT =
    27.0;


var PROTOTYPE_MAX_LAT =
    33.0;


var PROTOTYPE_MIN_LON =
    73.0;


var PROTOTYPE_MAX_LON =
    79.0;


// ============================================================
// COVERAGE CHECK
// ============================================================

function isInsidePrototypeRegion(
    latitude,
    longitude
) {

    return (

        latitude >=
        PROTOTYPE_MIN_LAT

        &&

        latitude <=
        PROTOTYPE_MAX_LAT

        &&

        longitude >=
        PROTOTYPE_MIN_LON

        &&

        longitude <=
        PROTOTYPE_MAX_LON

    );

}


// ============================================================
// MODEL COVERAGE RECTANGLE
// ============================================================

var prototypeRegion =
    L.rectangle(

        [

            [
                PROTOTYPE_MIN_LAT,
                PROTOTYPE_MIN_LON
            ],

            [
                PROTOTYPE_MAX_LAT,
                PROTOTYPE_MAX_LON
            ]

        ],

        {

            color:
                "#00eaff",

            weight:
                2,

            opacity:
                0.75,

            fillColor:
                "#00eaff",

            fillOpacity:
                0.015,

            dashArray:
                "7,7",

            interactive:
                false

        }

    );


prototypeRegion

.bindTooltip(

    "Current AeroVision ML coverage: Delhi + Haryana + Punjab",

    {

        direction:
            "center"

    }

)

.addTo(
    map
);


// ============================================================
// AQI COLORS
// ============================================================

function aqiColor(
    aqi
) {

    aqi =
        Number(
            aqi
        );


    if (
        !Number.isFinite(
            aqi
        )
    ) {

        return "#808080";

    }


    if (
        aqi <= 50
    ) {

        return "#00b050";

    }


    if (
        aqi <= 100
    ) {

        return "#8cc63f";

    }


    if (
        aqi <= 200
    ) {

        return "#f9d423";

    }


    if (
        aqi <= 300
    ) {

        return "#ff8c00";

    }


    if (
        aqi <= 400
    ) {

        return "#d32f2f";

    }


    return "#7e0023";

}


// ============================================================
// HEX → RGB
// ============================================================

function hexToRgb(
    hex
) {

    var clean =
        String(
            hex
        )
        .replace(
            "#",
            ""
        );


    if (
        clean.length === 3
    ) {

        clean =
            clean
            .split(
                ""
            )
            .map(

                function(ch) {

                    return (
                        ch +
                        ch
                    );

                }

            )
            .join(
                ""
            );

    }


    return {

        r:
            parseInt(
                clean.substring(
                    0,
                    2
                ),
                16
            ),

        g:
            parseInt(
                clean.substring(
                    2,
                    4
                ),
                16
            ),

        b:
            parseInt(
                clean.substring(
                    4,
                    6
                ),
                16
            )

    };

}


// ============================================================
// RGB INTERPOLATION
// ============================================================

function interpolateRgb(
    colorA,
    colorB,
    t
) {

    var a =
        hexToRgb(
            colorA
        );


    var b =
        hexToRgb(
            colorB
        );


    t =
        Math.max(
            0,
            Math.min(
                1,
                t
            )
        );


    return {

        r:
            Math.round(
                a.r +
                (
                    b.r -
                    a.r
                )
                *
                t
            ),

        g:
            Math.round(
                a.g +
                (
                    b.g -
                    a.g
                )
                *
                t
            ),

        b:
            Math.round(
                a.b +
                (
                    b.b -
                    a.b
                )
                *
                t
            )

    };

}


// ============================================================
// CONTINUOUS AQI COLOR
// ============================================================

function smoothAQIRgb(
    aqi
) {

    var value =
        Number(
            aqi
        );


    if (
        !Number.isFinite(
            value
        )
    ) {

        return {

            r:
                128,

            g:
                128,

            b:
                128

        };

    }


    value =
        Math.max(

            0,

            Math.min(
                500,
                value
            )

        );


    var stops =
        [

            {
                value: 0,
                color: "#00b050"
            },

            {
                value: 50,
                color: "#00b050"
            },

            {
                value: 100,
                color: "#8cc63f"
            },

            {
                value: 200,
                color: "#f9d423"
            },

            {
                value: 300,
                color: "#ff8c00"
            },

            {
                value: 400,
                color: "#d32f2f"
            },

            {
                value: 500,
                color: "#7e0023"
            }

        ];


    for (
        var i = 0;
        i < stops.length - 1;
        i++
    ) {

        var left =
            stops[
                i
            ];


        var right =
            stops[
                i + 1
            ];


        if (

            value >=
            left.value

            &&

            value <=
            right.value

        ) {

            var span =
                right.value -
                left.value;


            var t =
                span > 0

                    ?

                    (
                        value -
                        left.value
                    )

                    /

                    span

                    :

                    0;


            return interpolateRgb(

                left.color,

                right.color,

                t

            );

        }

    }


    return hexToRgb(
        "#7e0023"
    );

}


// ============================================================
// MISSING VALUE
// ============================================================

function isMissingValue(
    value
) {

    if (

        value === null

        ||

        value === undefined

        ||

        value === ""

    ) {

        return true;

    }


    if (
        typeof value ===
        "string"
    ) {

        var normalized =
            value
            .trim()
            .toLowerCase();


        if (

            normalized === ""

            ||

            normalized === "null"

            ||

            normalized === "none"

            ||

            normalized === "nan"

            ||

            normalized === "n/a"

            ||

            normalized === "undefined"

        ) {

            return true;

        }

    }


    return false;

}


// ============================================================
// VALID NUMBER
// ============================================================

function validNumericValue(
    value
) {

    if (
        isMissingValue(
            value
        )
    ) {

        return null;

    }


    var number =
        Number(
            value
        );


    if (
        !Number.isFinite(
            number
        )
    ) {

        return null;

    }


    return number;

}


// ============================================================
// SAFE NUMBER
// ============================================================

function safeNumber(
    value,
    decimals
) {

    if (
        decimals === undefined
    ) {

        decimals =
            1;

    }


    var number =
        validNumericValue(
            value
        );


    if (
        number === null
    ) {

        return "N/A";

    }


    return number.toFixed(
        decimals
    );

}


// ============================================================
// SAFE TEXT
// ============================================================

function safeText(
    value
) {

    if (
        isMissingValue(
            value
        )
    ) {

        return "N/A";

    }


    return String(
        value
    );

}


// ============================================================
// SET TEXT
// ============================================================

function setText(
    id,
    value
) {

    var element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.textContent =
            value;

    }

}


// ============================================================
// RESET POLLUTANT PANEL
// ============================================================

function resetSelectedPollutants(
    value
) {

    [

        "selectedPM25",

        "selectedPM10",

        "selectedNO2",

        "selectedO3",

        "selectedPredPM25",

        "selectedPredPM10",

        "selectedPredNO2",

        "selectedPredO3"

    ]

    .forEach(

        function(id) {

            setText(
                id,
                value
            );

        }

    );

}


// ============================================================
// AQI ERROR
// ============================================================

function getAQIError(
    p
) {

    var value =
        validNumericValue(

            p.ABS_ERROR !== undefined

                ?

                p.ABS_ERROR

                :

                p.AQI_ABS_ERROR

        );


    if (
        value !== null
    ) {

        return Math.abs(
            value
        );

    }


    value =
        validNumericValue(
            p.AQI_DIFFERENCE
        );


    if (
        value !== null
    ) {

        return Math.abs(
            value
        );

    }


    var cpcb =
        validNumericValue(
            p.CPCB_AQI
        );


    var aero =
        validNumericValue(
            p.AEROVISION_AQI
        );


    if (

        cpcb !== null

        &&

        aero !== null

    ) {

        return Math.abs(
            aero -
            cpcb
        );

    }


    return null;

}


// ============================================================
// CPCB REFERENCE STATUS
// ============================================================

function getCPCBReferenceStatus(
    p
) {

    if (

        p.CPCB_REFERENCE_STATUS

        &&

        String(
            p.CPCB_REFERENCE_STATUS
        )
        .toUpperCase() ===
        "FULL"

    ) {

        return {

            full:
                true,

            count:
                4,

            text:
                "FULL CPCB REFERENCE"

        };

    }


    var count =
        0;


    if (
        validNumericValue(
            p.PM25
        ) !== null
    ) {

        count++;

    }


    if (
        validNumericValue(
            p.PM10
        ) !== null
    ) {

        count++;

    }


    if (
        validNumericValue(
            p.NO2
        ) !== null
    ) {

        count++;

    }


    if (
        validNumericValue(
            p.O3_8H
        ) !== null
    ) {

        count++;

    }


    return {

        full:
            count === 4,

        count:
            count,

        text:

            count === 4

                ?

                "FULL CPCB REFERENCE"

                :

                (
                    "PARTIAL CPCB REFERENCE (" +
                    count +
                    "/4 pollutants)"
                )

    };

}


// ============================================================
// DOMINANT POLLUTANT
// ============================================================

function getDominantPollutant(
    p
) {

    if (
        !isMissingValue(
            p.AEROVISION_DOMINANT
        )
    ) {

        return p.AEROVISION_DOMINANT;

    }


    if (
        !isMissingValue(
            p.CPCB_DOMINANT
        )
    ) {

        return p.CPCB_DOMINANT;

    }


    return "N/A";

}


// ============================================================
// BILINEAR INTERPOLATION
// ============================================================

function bilinearAQI(
    matrix,
    rows,
    cols,
    x,
    y
) {

    var gx =
        Math.max(

            0,

            Math.min(
                cols - 1,
                x
            )

        );


    var gy =
        Math.max(

            0,

            Math.min(
                rows - 1,
                y
            )

        );


    var x0 =
        Math.floor(
            gx
        );


    var y0 =
        Math.floor(
            gy
        );


    var x1 =
        Math.min(
            cols - 1,
            x0 + 1
        );


    var y1 =
        Math.min(
            rows - 1,
            y0 + 1
        );


    var tx =
        gx -
        x0;


    var ty =
        gy -
        y0;


    var q00 =
        matrix[
            y0
        ][
            x0
        ];


    var q10 =
        matrix[
            y0
        ][
            x1
        ];


    var q01 =
        matrix[
            y1
        ][
            x0
        ];


    var q11 =
        matrix[
            y1
        ][
            x1
        ];


    var values =
        [

            q00,
            q10,
            q01,
            q11

        ]

        .filter(

            function(v) {

                return Number.isFinite(
                    v
                );

            }

        );


    if (
        values.length === 0
    ) {

        return null;

    }


    if (
        !Number.isFinite(
            q00
        )
    ) {

        q00 =
            values[
                0
            ];

    }


    if (
        !Number.isFinite(
            q10
        )
    ) {

        q10 =
            values[
                0
            ];

    }


    if (
        !Number.isFinite(
            q01
        )
    ) {

        q01 =
            values[
                0
            ];

    }


    if (
        !Number.isFinite(
            q11
        )
    ) {

        q11 =
            values[
                0
            ];

    }


    var top =
        q00 *
        (
            1 -
            tx
        )

        +

        q10 *
        tx;


    var bottom =
        q01 *
        (
            1 -
            tx
        )

        +

        q11 *
        tx;


    return (

        top *
        (
            1 -
            ty
        )

        +

        bottom *
        ty

    );

}


// ============================================================
// CREATE SMOOTH AQI RASTER
// ============================================================

function createSmoothAQIRaster(
    features
) {

    var records =
        [];


    features.forEach(

        function(feature) {

            var p =
                feature.properties
                ||
                {};


            var aqi =
                validNumericValue(
                    p.AQI
                );


            var lat =
                validNumericValue(
                    p.latitude
                );


            var lon =
                validNumericValue(
                    p.longitude
                );


            if (

                lat === null

                ||

                lon === null

            ) {

                var temporary =
                    L.geoJSON(
                        feature
                    );


                var center =
                    temporary
                    .getBounds()
                    .getCenter();


                lat =
                    center.lat;


                lon =
                    center.lng;

            }


            if (

                aqi !== null

                &&

                lat !== null

                &&

                lon !== null

            ) {

                records.push(

                    {

                        lat:
                            lat,

                        lon:
                            lon,

                        aqi:
                            aqi

                    }

                );

            }

        }

    );


    if (
        records.length === 0
    ) {

        throw new Error(
            "No valid AQI records."
        );

    }


    var lats =
        Array.from(

            new Set(

                records.map(

                    function(record) {

                        return Number(

                            record.lat
                            .toFixed(
                                8
                            )

                        );

                    }

                )

            )

        )

        .sort(

            function(a, b) {

                return b - a;

            }

        );


    var lons =
        Array.from(

            new Set(

                records.map(

                    function(record) {

                        return Number(

                            record.lon
                            .toFixed(
                                8
                            )

                        );

                    }

                )

            )

        )

        .sort(

            function(a, b) {

                return a - b;

            }

        );


    var rows =
        lats.length;


    var cols =
        lons.length;


    console.log(

        "AQI raster grid:",

        rows +
        " x " +
        cols

    );


    var latIndex =
        {};


    var lonIndex =
        {};


    lats.forEach(

        function(lat, index) {

            latIndex[
                lat.toFixed(
                    8
                )
            ] =
                index;

        }

    );


    lons.forEach(

        function(lon, index) {

            lonIndex[
                lon.toFixed(
                    8
                )
            ] =
                index;

        }

    );


    var matrix =
        Array.from(

            {
                length:
                    rows
            },

            function() {

                return Array(
                    cols
                )
                .fill(
                    null
                );

            }

        );


    records.forEach(

        function(record) {

            var row =
                latIndex[
                    record.lat
                    .toFixed(
                        8
                    )
                ];


            var col =
                lonIndex[
                    record.lon
                    .toFixed(
                        8
                    )
                ];


            matrix[
                row
            ][
                col
            ] =
                record.aqi;

        }

    );


    var latStep =
        rows > 1

            ?

            Math.abs(
                lats[0] -
                lats[1]
            )

            :

            0.25;


    var lonStep =
        cols > 1

            ?

            Math.abs(
                lons[1] -
                lons[0]
            )

            :

            0.25;


    var north =
        lats[0] +
        latStep / 2;


    var south =
        lats[
            rows - 1
        ]
        -
        latStep / 2;


    var west =
        lons[0] -
        lonStep / 2;


    var east =
        lons[
            cols - 1
        ]
        +
        lonStep / 2;


    // Increase for sharper output if required.
    var width =
        1000;


    var height =
        1000;


    var canvas =
        document.createElement(
            "canvas"
        );


    canvas.width =
        width;


    canvas.height =
        height;


    var context =
        canvas.getContext(
            "2d"
        );


    var image =
        context.createImageData(
            width,
            height
        );


    var pixels =
        image.data;


    for (
        var py = 0;
        py < height;
        py++
    ) {

        var gy =
            (
                py /
                (
                    height -
                    1
                )
            )

            *

            (
                rows -
                1
            );


        for (
            var px = 0;
            px < width;
            px++
        ) {

            var gx =
                (
                    px /
                    (
                        width -
                        1
                    )
                )

                *

                (
                    cols -
                    1
                );


            var aqi =
                bilinearAQI(

                    matrix,

                    rows,

                    cols,

                    gx,

                    gy

                );


            if (
                aqi === null
            ) {

                continue;

            }


            var rgb =
                smoothAQIRgb(
                    aqi
                );


            // Fade only the outer edge.
            var nx =
                px /
                (
                    width -
                    1
                );


            var ny =
                py /
                (
                    height -
                    1
                );


            var edgeDistance =
                Math.min(

                    nx,

                    1 - nx,

                    ny,

                    1 - ny

                );


            var edgeFade =
                Math.min(

                    1,

                    Math.max(

                        0,

                        edgeDistance /
                        0.035

                    )

                );


            var alpha =
                Math.round(

                    190 *
                    edgeFade

                );


            var index =
                (
                    py *
                    width +
                    px
                )

                *
                4;


            pixels[
                index
            ] =
                rgb.r;


            pixels[
                index + 1
            ] =
                rgb.g;


            pixels[
                index + 2
            ] =
                rgb.b;


            pixels[
                index + 3
            ] =
                alpha;

        }

    }


    context.putImageData(

        image,

        0,

        0

    );


    return {

        dataUrl:
            canvas.toDataURL(
                "image/png"
            ),

        bounds:
            [

                [
                    south,
                    west
                ],

                [
                    north,
                    east
                ]

            ],

        rows:
            rows,

        cols:
            cols,

        count:
            records.length

    };

}


// ============================================================
// CPCB SELECTED STATION
// ============================================================

function updateSelectedStation(
    p
) {

    hidePredictionPipeline();


    setText(
        "selectedStation",
        safeText(
            p.station
        )
    );


    setText(
        "selectedCpcbAqi",
        safeNumber(
            p.CPCB_AQI,
            0
        )
    );


    setText(
        "selectedAeroAqi",
        safeNumber(
            p.AEROVISION_AQI,
            0
        )
    );


    var reference =
        getCPCBReferenceStatus(
            p
        );


    var error =
        reference.full

            ?

            getAQIError(
                p
            )

            :

            null;


    setText(

        "selectedAqiError",

        error !== null

            ?

            error.toFixed(
                1
            )

            :

            "N/A"

    );


    setText(
        "selectedLocationName",
        safeText(
            p.station
        )
    );


    setText(
        "selectedLocationDate",
        safeText(
            p.date_text
        )
    );


    setText(
        "selectedCpcbCategory",
        safeText(
            p.CPCB_CATEGORY
        )
    );


    setText(
        "selectedAeroCategory",
        safeText(
            p.AEROVISION_CATEGORY
        )
    );


    setText(

        "selectedDominant",

        safeText(
            getDominantPollutant(
                p
            )
        )

    );


    setText(
        "selectedPM25",
        safeNumber(
            p.PM25
        )
    );


    setText(
        "selectedPM10",
        safeNumber(
            p.PM10
        )
    );


    setText(
        "selectedNO2",
        safeNumber(
            p.NO2
        )
    );


    setText(
        "selectedO3",
        safeNumber(
            p.O3_8H
        )
    );


    setText(
        "selectedPredPM25",
        safeNumber(
            p.PRED_PM25
        )
    );


    setText(
        "selectedPredPM10",
        safeNumber(
            p.PRED_PM10
        )
    );


    setText(
        "selectedPredNO2",
        safeNumber(
            p.PRED_NO2
        )
    );


    setText(
        "selectedPredO3",
        safeNumber(
            p.PRED_O3_8H
        )
    );

}


// ============================================================
// VALIDATION SUMMARY
// ============================================================

fetch(
    "/data/exports/validation_summary.json"
)

.then(

    function(response) {

        if (
            !response.ok
        ) {

            throw new Error(
                "Validation HTTP " +
                response.status
            );

        }


        return response.json();

    }

)

.then(

    function(data) {

        console.log(
            "✅ Validation summary loaded:",
            data
        );

    }

)

.catch(

    function(error) {

        console.error(
            "Validation summary error:",
            error
        );

    }

);


// ============================================================
// CPCB STATIONS
// ============================================================

fetch(
    "/data/exports/cpcb_comparison.geojson"
)

.then(

    function(response) {

        if (
            !response.ok
        ) {

            throw new Error(
                "CPCB HTTP " +
                response.status
            );

        }


        return response.json();

    }

)

.then(

    function(data) {


        var geoLayer =
            L.geoJSON(

                data,

                {

                    pointToLayer:
                    function(
                        feature,
                        latlng
                    ) {

                        var p =
                            feature.properties;


                        return L.circleMarker(

                            latlng,

                            {

                                pane:
                                    "cpcbPane",

                                radius:
                                    11,

                                color:
                                    "#111",

                                weight:
                                    3,

                                fillColor:
                                    aqiColor(
                                        p.AEROVISION_AQI
                                    ),

                                fillOpacity:
                                    1,

                                bubblingMouseEvents:
                                    false

                            }

                        );

                    },


                    onEachFeature:
                    function(
                        feature,
                        layer
                    ) {

                        var p =
                            feature.properties;


                        var reference =
                            getCPCBReferenceStatus(
                                p
                            );


                        var error =
                            reference.full

                                ?

                                getAQIError(
                                    p
                                )

                                :

                                null;


                        var popup =
                            `

                            <div class="aqi-popup">

                                <h3>
                                    ${safeText(p.station)}
                                </h3>

                                <div class="popup-date">
                                    ${safeText(p.date_text)}
                                </div>

                                <div
                                    style="
                                        margin:7px 0;
                                        padding:6px;
                                        border-radius:6px;
                                        text-align:center;
                                        font-size:10px;
                                        font-weight:700;
                                        color:${
                                            reference.full
                                            ?
                                            "#00b050"
                                            :
                                            "#ff9800"
                                        };
                                    "
                                >
                                    ${reference.text}
                                </div>


                                <div class="aqi-comparison">

                                    <div class="aqi-side">

                                        <small>
                                            CPCB REFERENCE
                                        </small>

                                        <strong>
                                            ${safeNumber(p.CPCB_AQI,0)}
                                        </strong>

                                        <span>
                                            ${safeText(p.CPCB_CATEGORY)}
                                        </span>

                                    </div>


                                    <div class="versus">
                                        VS
                                    </div>


                                    <div class="aqi-side">

                                        <small>
                                            AEROVISION
                                        </small>

                                        <strong>
                                            ${safeNumber(p.AEROVISION_AQI,0)}
                                        </strong>

                                        <span>
                                            ${safeText(p.AEROVISION_CATEGORY)}
                                        </span>

                                    </div>

                                </div>


                                ${
                                    reference.full

                                    ?

                                    `
                                    <div class="aqi-difference">

                                        AQI Difference:

                                        <strong>
                                            ${
                                                error !== null
                                                ?
                                                error.toFixed(1)
                                                :
                                                "N/A"
                                            }
                                        </strong>

                                    </div>
                                    `

                                    :

                                    `
                                    <div
                                        class="aqi-difference"
                                        style="color:#ff9800;"
                                    >

                                        ⚠ Partial CPCB pollutant reference

                                        <br>

                                        <small>
                                            Error excluded from
                                            full-reference validation
                                        </small>

                                    </div>
                                    `
                                }


                                <hr>


                                <table class="pollutant-table">

                                    <tr>
                                        <th>Pollutant</th>
                                        <th>CPCB</th>
                                        <th>AeroVision</th>
                                    </tr>

                                    <tr>
                                        <td>PM2.5</td>
                                        <td>${safeNumber(p.PM25)}</td>
                                        <td>${safeNumber(p.PRED_PM25)}</td>
                                    </tr>

                                    <tr>
                                        <td>PM10</td>
                                        <td>${safeNumber(p.PM10)}</td>
                                        <td>${safeNumber(p.PRED_PM10)}</td>
                                    </tr>

                                    <tr>
                                        <td>NO₂</td>
                                        <td>${safeNumber(p.NO2)}</td>
                                        <td>${safeNumber(p.PRED_NO2)}</td>
                                    </tr>

                                    <tr>
                                        <td>O₃ 8H</td>
                                        <td>${safeNumber(p.O3_8H)}</td>
                                        <td>${safeNumber(p.PRED_O3_8H)}</td>
                                    </tr>

                                </table>


                                <div class="popup-footnote">

                                    CPCB = measured/derived reference

                                    <br>

                                    AeroVision = XGBoost prediction

                                </div>

                            </div>
                            `;


                        layer.bindPopup(

                            popup,

                            {
                                maxWidth:
                                    360
                            }

                        );


                        layer.on(

                            "click",

                            function(event) {

                                if (
                                    event &&
                                    event.originalEvent
                                ) {

                                    L.DomEvent.stopPropagation(
                                        event.originalEvent
                                    );

                                }


                                updateSelectedStation(
                                    p
                                );

                            }

                        );

                    }

                }

            );


        geoLayer.addTo(
            cpcbLayer
        );


        cpcbLayer.addTo(
            map
        );


        console.log(

            "✅ CPCB stations loaded:",

            data.features.length

        );

    }

)

.catch(

    function(error) {

        console.error(
            "❌ CPCB error:",
            error
        );

    }

);


// ============================================================
// HCHO
// ============================================================

fetch(
    "/data/exports/hcho_hotspots_event.geojson"
)

.then(

    function(response) {

        if (
            !response.ok
        ) {

            throw new Error(
                "HCHO HTTP " +
                response.status
            );

        }


        return response.json();

    }

)

.then(

    function(data) {


        L.geoJSON(

            data,

            {

                pointToLayer:
                function(
                    feature,
                    latlng
                ) {

                    var p =
                        feature.properties;


                    var associated =
                        Number(
                            p.HCHO_FIRE_ASSOC
                        ) === 1;


                    return L.circleMarker(

                        latlng,

                        {

                            pane:
                                "hchoPane",

                            radius:
                                associated
                                ?
                                3.5
                                :
                                2.3,

                            color:
                                associated
                                ?
                                "#ffffff"
                                :
                                "#d500f9",

                            fillColor:
                                associated
                                ?
                                "#ffffff"
                                :
                                "#d500f9",

                            fillOpacity:
                                associated
                                ?
                                0.9
                                :
                                0.55,

                            weight:
                                0.5,

                            bubblingMouseEvents:
                                false

                        }

                    );

                },


                onEachFeature:
                function(
                    feature,
                    layer
                ) {

                    var p =
                        feature.properties;


                    var associated =
                        Number(
                            p.HCHO_FIRE_ASSOC
                        ) === 1;


                    var value =
                        validNumericValue(
                            p.HCHO
                        );


                    layer.bindPopup(

                        "<b>TROPOMI HCHO Hotspot</b><br>" +

                        "Date: 08 June 2026<br>" +

                        "HCHO: " +

                        (
                            value !== null

                            ?

                            value.toExponential(
                                3
                            )

                            :

                            "N/A"
                        )

                        +

                        " mol/m²<br><br>" +

                        (
                            associated

                            ?

                            "<b>Within 25 km of detected fire</b>"

                            :

                            "No detected fire within 25 km"
                        )

                    );

                }

            }

        )

        .addTo(
            hchoLayer
        );


        console.log(
            "✅ HCHO loaded:",
            data.features.length
        );

    }

)

.catch(

    function(error) {

        console.error(
            "❌ HCHO error:",
            error
        );

    }

);


// ============================================================
// FIRMS
// ============================================================

Papa.parse(

    "/data/exports/fire_event.csv",

    {

        download:
            true,

        header:
            true,


        complete:
        function(results) {

            var count =
                0;


            results.data.forEach(

                function(row) {

                    var lat =
                        validNumericValue(
                            row.latitude
                        );


                    var lon =
                        validNumericValue(
                            row.longitude
                        );


                    if (

                        lat === null

                        ||

                        lon === null

                    ) {

                        return;

                    }


                    var confidence =
                        validNumericValue(
                            row.confidence
                        );


                    var temperature =
                        validNumericValue(
                            row.temperature
                        );


                    var marker =
                        L.circleMarker(

                            [
                                lat,
                                lon
                            ],

                            {

                                pane:
                                    "firePane",

                                radius:
                                    4,

                                color:
                                    "#ffcc00",

                                weight:
                                    1,

                                fillColor:
                                    "#ff3d00",

                                fillOpacity:
                                    0.9,

                                bubblingMouseEvents:
                                    false

                            }

                        );


                    marker.bindPopup(

                        "<b>NASA FIRMS Fire Detection</b><br>" +

                        "Date: 08 June 2026<br>" +

                        "Confidence: " +

                        (
                            confidence !== null

                            ?

                            confidence.toFixed(
                                0
                            ) + "%"

                            :

                            "N/A"
                        )

                        +

                        "<br>T21: " +

                        (
                            temperature !== null

                            ?

                            temperature.toFixed(
                                1
                            ) + " K"

                            :

                            "N/A"
                        )

                    );


                    marker.addTo(
                        fireLayer
                    );


                    count++;

                }

            );


            console.log(
                "✅ FIRMS loaded:",
                count
            );

        },


        error:
        function(error) {

            console.error(
                "❌ FIRMS error:",
                error
            );

        }

    }

);


// ============================================================
// ERA5 WIND
// ============================================================

Papa.parse(

    "/data/exports/wind_event.csv",

    {

        download:
            true,

        header:
            true,


        complete:
        function(results) {

            var count =
                0;


            results.data.forEach(

                function(row) {

                    var lat =
                        validNumericValue(
                            row.latitude
                        );


                    var lon =
                        validNumericValue(
                            row.longitude
                        );


                    var u =
                        validNumericValue(
                            row.u
                        );


                    var v =
                        validNumericValue(
                            row.v
                        );


                    var speed =
                        validNumericValue(
                            row.speed
                        );


                    if (

                        lat === null

                        ||

                        lon === null

                        ||

                        u === null

                        ||

                        v === null

                    ) {

                        return;

                    }


                    var angle =
                        Math.atan2(
                            v,
                            u
                        )

                        *

                        180

                        /

                        Math.PI;


                    var size =
                        Math.max(

                            10,

                            Math.min(

                                17,

                                10 +
                                (
                                    speed !== null
                                    ?
                                    speed
                                    :
                                    0
                                )

                            )

                        );


                    var icon =
                        L.divIcon(

                            {

                                className:
                                    "wind-arrow",

                                html:
                                    `

                                    <div
                                        class="wind-arrow-inner"
                                        style="
                                            transform:rotate(${angle}deg);
                                            font-size:${size}px;
                                        "
                                    >
                                        ➤
                                    </div>
                                    `,

                                iconSize:
                                    [
                                        18,
                                        18
                                    ],

                                iconAnchor:
                                    [
                                        9,
                                        9
                                    ]

                            }

                        );


                    var marker =
                        L.marker(

                            [
                                lat,
                                lon
                            ],

                            {

                                icon:
                                    icon,

                                pane:
                                    "windPane",

                                bubblingMouseEvents:
                                    false

                            }

                        );


                    marker.bindPopup(

                        "<b>ERA5-Land Wind</b><br>" +

                        "Date: 08 June 2026<br>" +

                        "U: " +
                        u.toFixed(2) +
                        " m/s<br>" +

                        "V: " +
                        v.toFixed(2) +
                        " m/s<br>" +

                        "Speed: " +

                        (
                            speed !== null

                            ?

                            speed.toFixed(2)

                            :

                            "N/A"
                        )

                        +

                        " m/s"

                    );


                    marker.addTo(
                        windLayer
                    );


                    count++;

                }

            );


            console.log(
                "✅ ERA5 wind loaded:",
                count
            );

        }

    }

);


// ============================================================
// SMOOTH REGIONAL AQI SURFACE
// ============================================================

console.log(
    "Loading smooth regional AQI surface..."
);


fetch(
    "/data/exports/aqi_surface_2026_06_08.geojson"
)

.then(

    function(response) {

        if (
            !response.ok
        ) {

            throw new Error(
                "AQI Surface HTTP " +
                response.status
            );

        }


        return response.json();

    }

)

.then(

    function(data) {


        console.log(

            "✅ AQI GeoJSON received:",

            data.features.length,

            "cells"

        );


        aqiSurfaceLayer.clearLayers();


        aqiSurfaceInteractiveLayer.clearLayers();


        // ====================================================
        // CREATE SMOOTH RASTER
        // ====================================================

        var raster =
            createSmoothAQIRaster(
                data.features
            );


        aqiSurfaceRaster =
            L.imageOverlay(

                raster.dataUrl,

                raster.bounds,

                {

                    pane:
                        "aqiSurfacePane",

                    opacity:
                        0.78,

                    interactive:
                        false

                }

            );


        aqiSurfaceRaster.addTo(
            aqiSurfaceLayer
        );


        // ====================================================
        // INVISIBLE CLICKABLE ORIGINAL CELLS
        // ====================================================

        var interactiveGeo =
            L.geoJSON(

                data,

                {

                    pane:
                        "aqiSurfacePane",


                    style:
                    function() {

                        return {

                            pane:
                                "aqiSurfacePane",

                            fillColor:
                                "#ffffff",

                            fillOpacity:
                                0.001,

                            color:
                                "#ffffff",

                            opacity:
                                0,

                            weight:
                                0

                        };

                    },


                    onEachFeature:
                    function(
                        feature,
                        layer
                    ) {

                        var p =
                            feature.properties
                            ||
                            {};


                        var aqi =
                            validNumericValue(
                                p.AQI
                            );


                        var popup =
                            `

                            <div class="aqi-popup">

                                <h3>
                                    AeroVision AQI Surface
                                </h3>


                                <div class="popup-date">
                                    08 June 2026
                                </div>


                                <div
                                    style="
                                        text-align:center;
                                        margin:12px 0;
                                    "
                                >

                                    <div
                                        style="
                                            width:70px;
                                            height:70px;
                                            margin:auto;
                                            border-radius:50%;
                                            display:flex;
                                            align-items:center;
                                            justify-content:center;
                                            background:${aqiColor(aqi)};
                                            font-size:22px;
                                            font-weight:800;
                                            color:#111;
                                        "
                                    >

                                        ${
                                            aqi !== null
                                            ?
                                            Math.round(
                                                aqi
                                            )
                                            :
                                            "N/A"
                                        }

                                    </div>


                                    <div
                                        style="
                                            margin-top:6px;
                                            font-weight:700;
                                        "
                                    >

                                        ${safeText(
                                            p.AQI_CATEGORY
                                        )}

                                    </div>


                                    <div
                                        style="
                                            margin-top:3px;
                                            font-size:10px;
                                            color:#777;
                                        "
                                    >

                                        Dominant:
                                        ${safeText(
                                            p.DOMINANT_POLLUTANT
                                        )}

                                    </div>

                                </div>


                                <table class="pollutant-table">

                                    <tr>
                                        <th>Pollutant</th>
                                        <th>AeroVision</th>
                                    </tr>

                                    <tr>
                                        <td>PM2.5</td>
                                        <td>${safeNumber(p.PRED_PM25)}</td>
                                    </tr>

                                    <tr>
                                        <td>PM10</td>
                                        <td>${safeNumber(p.PRED_PM10)}</td>
                                    </tr>

                                    <tr>
                                        <td>NO₂</td>
                                        <td>${safeNumber(p.PRED_NO2)}</td>
                                    </tr>

                                    <tr>
                                        <td>O₃ 8H</td>
                                        <td>${safeNumber(p.PRED_O3_8H)}</td>
                                    </tr>

                                </table>


                                <hr>


                                <div
                                    style="
                                        font-size:10px;
                                        line-height:1.6;
                                        color:#666;
                                    "
                                >

                                    <strong>
                                        Environmental context
                                    </strong>

                                    <br>

                                    MODIS AOD:
                                    ${safeNumber(p.AOD,3)}

                                    <br>

                                    Wind:
                                    ${safeNumber(p.WIND_SPEED,2)} m/s

                                    <br>

                                    HCHO:
                                    ${safeNumber(p.HCHO,6)}

                                    <br>

                                    Satellite NO₂:
                                    ${safeNumber(p.SAT_NO2,6)}

                                    <br>

                                    Fires within 25 km:
                                    ${safeNumber(p.FIRE_COUNT_25KM,0)}

                                </div>


                                <div class="popup-footnote">

                                    Original AeroVision V3 grid-cell prediction

                                    <br>

                                    Smooth color surface between cells is
                                    bilinearly interpolated for visualization only

                                    <br>

                                    Environmental inputs come from
                                    Google Earth Engine datasets

                                </div>

                            </div>
                            `;


                        layer.bindPopup(

                            popup,

                            {
                                maxWidth:
                                    340
                            }

                        );


                        layer.on(

                            "click",

                            function(event) {


                                if (

                                    event

                                    &&

                                    event.originalEvent

                                ) {

                                    L.DomEvent.stopPropagation(
                                        event.originalEvent
                                    );

                                }


                                hidePredictionPipeline();


                                var lat =
                                    validNumericValue(
                                        p.latitude
                                    );


                                var lon =
                                    validNumericValue(
                                        p.longitude
                                    );


                                if (

                                    lat === null

                                    ||

                                    lon === null

                                ) {

                                    var center =
                                        layer
                                        .getBounds()
                                        .getCenter();


                                    lat =
                                        center.lat;


                                    lon =
                                        center.lng;

                                }


                                var locationLabel =
                                    lat.toFixed(
                                        2
                                    )

                                    +

                                    "°N, "

                                    +

                                    lon.toFixed(
                                        2
                                    )

                                    +

                                    "°E";


                                setText(
                                    "selectedStation",
                                    locationLabel
                                );


                                setText(
                                    "selectedCpcbAqi",
                                    "N/A"
                                );


                                setText(
                                    "selectedAeroAqi",
                                    safeNumber(
                                        p.AQI,
                                        0
                                    )
                                );


                                setText(
                                    "selectedAqiError",
                                    "N/A"
                                );


                                setText(
                                    "selectedLocationName",
                                    locationLabel
                                );


                                setText(
                                    "selectedLocationDate",
                                    "08 June 2026"
                                );


                                setText(
                                    "selectedCpcbCategory",
                                    "N/A"
                                );


                                setText(
                                    "selectedAeroCategory",
                                    safeText(
                                        p.AQI_CATEGORY
                                    )
                                );


                                setText(
                                    "selectedDominant",
                                    safeText(
                                        p.DOMINANT_POLLUTANT
                                    )
                                );


                                setText(
                                    "selectedPM25",
                                    "N/A"
                                );


                                setText(
                                    "selectedPM10",
                                    "N/A"
                                );


                                setText(
                                    "selectedNO2",
                                    "N/A"
                                );


                                setText(
                                    "selectedO3",
                                    "N/A"
                                );


                                setText(
                                    "selectedPredPM25",
                                    safeNumber(
                                        p.PRED_PM25
                                    )
                                );


                                setText(
                                    "selectedPredPM10",
                                    safeNumber(
                                        p.PRED_PM10
                                    )
                                );


                                setText(
                                    "selectedPredNO2",
                                    safeNumber(
                                        p.PRED_NO2
                                    )
                                );


                                setText(
                                    "selectedPredO3",
                                    safeNumber(
                                        p.PRED_O3_8H
                                    )
                                );


                                console.log(

                                    "🌫 AQI surface cell selected:",

                                    p

                                );

                            }

                        );

                    }

                }

            );


        interactiveGeo.eachLayer(

            function(layer) {

                aqiSurfaceInteractiveLayer.addLayer(
                    layer
                );

            }

        );


        aqiSurfaceLayer.addLayer(
            aqiSurfaceInteractiveLayer
        );


        console.log(
            "✅ SMOOTH AQI SURFACE READY"
        );


        console.log(
            "✅ Prediction cells:",
            raster.count
        );


        console.log(

            "✅ Grid:",

            raster.rows +
            " x " +
            raster.cols

        );

    }

)

.catch(

    function(error) {

        console.error(
            "❌ AQI surface error:",
            error
        );

    }

);


// ============================================================
// LIVE PREDICTION PIPELINE
// ============================================================

var predictionPipelineTimers =
    [];


function clearPredictionPipelineTimers() {

    predictionPipelineTimers.forEach(

        function(timer) {

            clearTimeout(
                timer
            );

        }

    );


    predictionPipelineTimers =
        [];

}


function setPipelineStage(
    text,
    progress
) {

    var panel =
        document.getElementById(
            "predictionPipeline"
        );


    var stage =
        document.getElementById(
            "pipelineStage"
        );


    var progressBar =
        document.getElementById(
            "pipelineProgressBar"
        );


    if (
        panel
    ) {

        panel.style.display =
            "block";

    }


    if (
        stage
    ) {

        stage.textContent =
            text;

    }


    if (
        progressBar
    ) {

        progressBar.style.width =
            progress +
            "%";

    }

}


function startPredictionPipeline() {

    clearPredictionPipelineTimers();


    var panel =
        document.getElementById(
            "predictionPipeline"
        );


    if (
        panel
    ) {

        panel.classList.remove(
            "pipeline-success",
            "pipeline-error"
        );

    }


    setPipelineStage(
        "📍 Reading clicked coordinates...",
        8
    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                setPipelineStage(

                    "🛰 Extracting MODIS & Sentinel-5P satellite features...",

                    25

                );

            },

            450

        )

    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                setPipelineStage(

                    "🌡 Reading ERA5-Land atmospheric conditions...",

                    45

                );

            },

            1200

        )

    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                setPipelineStage(

                    "🔥 Checking NASA FIRMS fire activity...",

                    63

                );

            },

            2000

        )

    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                setPipelineStage(

                    "🧠 Running AeroVision V3 XGBoost models...",

                    80

                );

            },

            2800

        )

    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                setPipelineStage(

                    "📊 Computing CPCB AQI sub-indices...",

                    92

                );

            },

            3800

        )

    );

}


function finishPredictionPipeline() {

    clearPredictionPipelineTimers();


    var panel =
        document.getElementById(
            "predictionPipeline"
        );


    if (
        panel
    ) {

        panel.classList.remove(
            "pipeline-error"
        );


        panel.classList.add(
            "pipeline-success"
        );

    }


    setPipelineStage(
        "✅ AQI prediction ready",
        100
    );


    predictionPipelineTimers.push(

        setTimeout(

            function() {

                var panel =
                    document.getElementById(
                        "predictionPipeline"
                    );


                if (
                    panel
                ) {

                    panel.style.display =
                        "none";

                }

            },

            2200

        )

    );

}


function failPredictionPipeline(
    message
) {

    clearPredictionPipelineTimers();


    var panel =
        document.getElementById(
            "predictionPipeline"
        );


    if (
        panel
    ) {

        panel.classList.remove(
            "pipeline-success"
        );


        panel.classList.add(
            "pipeline-error"
        );

    }


    setPipelineStage(

        "⚠ " +
        (
            message
            ||
            "Prediction unavailable"
        ),

        100

    );

}


function hidePredictionPipeline() {

    clearPredictionPipelineTimers();


    var panel =
        document.getElementById(
            "predictionPipeline"
        );


    if (
        panel
    ) {

        panel.style.display =
            "none";

    }

}


// ============================================================
// PREDICTION LOADING
// ============================================================

function showPredictionLoading(
    latitude,
    longitude
) {

    startPredictionPipeline();


    setText(
        "selectedStation",
        "Analyzing location..."
    );


    setText(
        "selectedCpcbAqi",
        "N/A"
    );


    setText(
        "selectedAeroAqi",
        "..."
    );


    setText(
        "selectedAqiError",
        "N/A"
    );


    setText(
        "selectedLocationName",
        "Extracting real environmental data..."
    );


    setText(

        "selectedLocationDate",

        latitude.toFixed(
            4
        )

        +

        ", "

        +

        longitude.toFixed(
            4
        )

    );


    setText(
        "selectedCpcbCategory",
        "N/A"
    );


    setText(
        "selectedAeroCategory",
        "Analyzing..."
    );


    setText(
        "selectedDominant",
        "..."
    );


    setText(
        "selectedPM25",
        "N/A"
    );


    setText(
        "selectedPM10",
        "N/A"
    );


    setText(
        "selectedNO2",
        "N/A"
    );


    setText(
        "selectedO3",
        "N/A"
    );


    setText(
        "selectedPredPM25",
        "..."
    );


    setText(
        "selectedPredPM10",
        "..."
    );


    setText(
        "selectedPredNO2",
        "..."
    );


    setText(
        "selectedPredO3",
        "..."
    );

}


// ============================================================
// OUTSIDE COVERAGE
// ============================================================

var predictionMarker =
    null;


function showOutsideCoverage(
    latitude,
    longitude
) {

    hidePredictionPipeline();


    if (
        predictionMarker
    ) {

        map.removeLayer(
            predictionMarker
        );


        predictionMarker =
            null;

    }


    var coordinates =
        latitude.toFixed(
            4
        )

        +

        ", "

        +

        longitude.toFixed(
            4
        );


    setText(
        "selectedStation",
        "Outside ML coverage"
    );


    setText(
        "selectedCpcbAqi",
        "N/A"
    );


    setText(
        "selectedAeroAqi",
        "N/A"
    );


    setText(
        "selectedAqiError",
        "N/A"
    );


    setText(
        "selectedLocationName",
        "Outside current ML coverage"
    );


    setText(
        "selectedLocationDate",
        coordinates
    );


    setText(
        "selectedCpcbCategory",
        "N/A"
    );


    setText(
        "selectedAeroCategory",
        "Not predicted"
    );


    setText(
        "selectedDominant",
        "N/A"
    );


    resetSelectedPollutants(
        "N/A"
    );


    L.popup(

        {
            maxWidth:
                320
        }

    )

    .setLatLng(

        [
            latitude,
            longitude
        ]

    )

    .setContent(

        `

        <div class="aqi-popup">

            <h3>
                🌍 AeroVision India
            </h3>

            <div
                style="
                    margin:10px 0;
                    padding:8px;
                    border-radius:7px;
                    background:rgba(255,152,0,.15);
                    color:#ff9800;
                    text-align:center;
                    font-weight:700;
                "
            >
                Outside Current ML Coverage
            </div>

            Current validated prediction region:

            <br>

            <strong>
                Delhi + Haryana + Punjab
            </strong>

            <br><br>

            Coordinates:

            <br>

            ${coordinates}

            <div class="popup-footnote">

                World basemap is available for navigation.

                <br>

                AeroVision predictions are currently restricted
                to the validated regional prototype.

            </div>

        </div>

        `

    )

    .openOn(
        map
    );

}


// ============================================================
// SHOW PREDICTION RESULT
// ============================================================

function showPredictionResult(
    data
) {

    finishPredictionPipeline();


    var prediction =
        data.prediction
        ||
        {};


    var locationName =

        data.location_name

        &&

        data.location_name !==
        "Selected Location"

            ?

            data.location_name

            :

            "Selected Location";


    setText(
        "selectedStation",
        locationName
    );


    setText(
        "selectedCpcbAqi",
        "N/A"
    );


    setText(
        "selectedAeroAqi",
        safeNumber(
            prediction.AQI,
            0
        )
    );


    setText(
        "selectedAqiError",
        "N/A"
    );


    setText(
        "selectedLocationName",
        locationName
    );


    setText(

        "selectedLocationDate",

        Number(
            data.latitude
        )
        .toFixed(
            4
        )

        +

        ", "

        +

        Number(
            data.longitude
        )
        .toFixed(
            4
        )

        +

        " | "

        +

        safeText(
            data.date
        )

    );


    setText(
        "selectedCpcbCategory",
        "N/A"
    );


    setText(
        "selectedAeroCategory",
        safeText(
            prediction.category
        )
    );


    setText(
        "selectedDominant",
        safeText(
            prediction.dominant_pollutant
        )
    );


    setText(
        "selectedPM25",
        "N/A"
    );


    setText(
        "selectedPM10",
        "N/A"
    );


    setText(
        "selectedNO2",
        "N/A"
    );


    setText(
        "selectedO3",
        "N/A"
    );


    setText(
        "selectedPredPM25",
        safeNumber(
            prediction.PM25
        )
    );


    setText(
        "selectedPredPM10",
        safeNumber(
            prediction.PM10
        )
    );


    setText(
        "selectedPredNO2",
        safeNumber(
            prediction.NO2
        )
    );


    setText(
        "selectedPredO3",
        safeNumber(
            prediction.O3_8H
        )
    );

}


// ============================================================
// EXACT-COORDINATE MARKER
// ============================================================

function showPredictionMarker(
    data
) {

    var prediction =
        data.prediction
        ||
        {};


    var env =
        data.environmental_features
        ||
        {};


    if (
        predictionMarker
    ) {

        map.removeLayer(
            predictionMarker
        );

    }


    predictionMarker =
        L.circleMarker(

            [

                Number(
                    data.latitude
                ),

                Number(
                    data.longitude
                )

            ],

            {

                pane:
                    "predictionPane",

                radius:
                    13,

                color:
                    "#00ffff",

                weight:
                    3,

                fillColor:
                    aqiColor(
                        prediction.AQI
                    ),

                fillOpacity:
                    0.95,

                bubblingMouseEvents:
                    false

            }

        );


    function displayValue(
        value,
        digits,
        suffix
    ) {

        var number =
            validNumericValue(
                value
            );


        if (
            number === null
        ) {

            return "No valid pixel";

        }


        return (

            number.toFixed(
                digits
            )

            +

            (
                suffix
                ||
                ""
            )

        );

    }


    var popup =
        `

        <div class="aqi-popup">

            <h3>
                ${safeText(
                    data.location_name
                    ||
                    "Selected Location"
                )}
            </h3>


            <div class="popup-date">

                Exact-coordinate prediction

                <br>

                ${Number(data.latitude).toFixed(5)},
                ${Number(data.longitude).toFixed(5)}

                <br>

                ${safeText(data.date)}

            </div>


            <div class="aqi-comparison">

                <div class="aqi-side">

                    <small>
                        AEROVISION AQI
                    </small>

                    <strong>
                        ${safeNumber(prediction.AQI,0)}
                    </strong>

                    <span>
                        ${safeText(prediction.category)}
                    </span>

                </div>

            </div>


            <div class="aqi-difference">

                Dominant Pollutant:

                <strong>
                    ${safeText(prediction.dominant_pollutant)}
                </strong>

            </div>


            <table class="pollutant-table">

                <tr>
                    <th>Pollutant</th>
                    <th>Prediction</th>
                </tr>

                <tr>
                    <td>PM2.5</td>
                    <td>${safeNumber(prediction.PM25)}</td>
                </tr>

                <tr>
                    <td>PM10</td>
                    <td>${safeNumber(prediction.PM10)}</td>
                </tr>

                <tr>
                    <td>NO₂</td>
                    <td>${safeNumber(prediction.NO2)}</td>
                </tr>

                <tr>
                    <td>O₃ 8H</td>
                    <td>${safeNumber(prediction.O3_8H)}</td>
                </tr>

            </table>


            <hr>


            <h4>
                Real Environmental Context
            </h4>


            <table class="pollutant-table">

                <tr>
                    <td>MODIS AOD</td>
                    <td>${displayValue(env.AOD,3,"")}</td>
                </tr>

                <tr>
                    <td>S5P HCHO</td>
                    <td>${displayValue(env.HCHO,6,"")}</td>
                </tr>

                <tr>
                    <td>S5P NO₂</td>
                    <td>${displayValue(env.SAT_NO2,6,"")}</td>
                </tr>

                <tr>
                    <td>Temperature</td>
                    <td>${displayValue(env.ERA5_TEMP,1," °C")}</td>
                </tr>

                <tr>
                    <td>Humidity</td>
                    <td>${displayValue(env.ERA5_RH,1," %")}</td>
                </tr>

                <tr>
                    <td>Wind Speed</td>
                    <td>${displayValue(env.WIND_SPEED,2," m/s")}</td>
                </tr>

                <tr>
                    <td>Nearby Fires</td>
                    <td>${displayValue(env.FIRE_COUNT_25KM,0,"")}</td>
                </tr>

            </table>


            <div class="popup-footnote">

                Environmental source:
                Google Earth Engine

                <br>

                Sampling:
                exact clicked coordinate

                <br>

                Model:
                AeroVision V3 XGBoost

            </div>

        </div>

        `;


    predictionMarker.bindPopup(

        popup,

        {
            maxWidth:
                390
        }

    );


    predictionMarker.addTo(
        map
    );


    predictionMarker.openPopup();

}


// ============================================================
// PREDICTION ERROR
// ============================================================

function showPredictionError(
    message
) {

    failPredictionPipeline(
        message
    );


    console.error(
        "Prediction error:",
        message
    );


    setText(
        "selectedStation",
        "Prediction unavailable"
    );


    setText(
        "selectedCpcbAqi",
        "N/A"
    );


    setText(
        "selectedAeroAqi",
        "N/A"
    );


    setText(
        "selectedAqiError",
        "N/A"
    );


    setText(
        "selectedLocationName",
        "Prediction unavailable"
    );


    setText(
        "selectedLocationDate",
        message
    );


    setText(
        "selectedCpcbCategory",
        "N/A"
    );


    setText(
        "selectedAeroCategory",
        "N/A"
    );


    setText(
        "selectedDominant",
        "N/A"
    );


    resetSelectedPollutants(
        "N/A"
    );

}


// ============================================================
// REQUEST PREDICTION
// ============================================================

// ============================================================
// REQUEST PREDICTION
// DATE-AWARE SAFE VERSION
// ============================================================

function requestAeroVisionPrediction(
    latitude,
    longitude,
    locationName
) {

    // Uses the date selected in the June timeline.
    // Falls back to 08 June 2026 if the timeline is unavailable.
    var selectedDate =
        window.AEROVISION_SELECTED_MAP_DATE
        ||
        "2026-06-08";


    console.log(
        "📅 Prediction date:",
        selectedDate
    );


    fetch(

        "/api/predict",

        {

            method:
                "POST",

            headers:
            {

                "Content-Type":
                    "application/json"

            },

            body:
                JSON.stringify(

                    {

                        latitude:
                            latitude,

                        longitude:
                            longitude,

                        date:
                            selectedDate

                    }

                )

        }

    )

    .then(

        function(response) {

            return response
            .json()

            .then(

                function(data) {

                    return {

                        ok:
                            response.ok,

                        data:
                            data

                    };

                }

            );

        }

    )

    .then(

        function(result) {

            if (

                !result.ok

                ||

                !result.data.success

            ) {

                throw new Error(

                    result.data.error

                    ||

                    "Prediction failed."

                );

            }


            result.data.location_name =

                locationName

                ||

                result.data.location_name

                ||

                "Selected Location";


            showPredictionResult(
                result.data
            );


            showPredictionMarker(
                result.data
            );

        }

    )

    .catch(

        function(error) {

            showPredictionError(
                error.message
            );

        }

    );

}


// ============================================================
// REVERSE GEOCODING
// ============================================================

async function getLocationName(
    latitude,
    longitude
) {

    try {


        var url =

            "https://nominatim.openstreetmap.org/reverse"

            +

            "?format=jsonv2"

            +

            "&lat=" +
            encodeURIComponent(
                latitude
            )

            +

            "&lon=" +
            encodeURIComponent(
                longitude
            )

            +

            "&zoom=10"

            +

            "&addressdetails=1";


        var response =
            await fetch(
                url
            );


        if (
            !response.ok
        ) {

            return "Selected Location";

        }


        var data =
            await response.json();


        var address =
            data.address
            ||
            {};


        var place =

            address.city

            ||

            address.town

            ||

            address.village

            ||

            address.municipality

            ||

            address.county

            ||

            address.state_district

            ||

            "Selected Location";


        var state =
            address.state
            ||
            "";


        if (

            state

            &&

            place !== state

        ) {

            return (

                place +
                ", " +
                state

            );

        }


        return place;

    }

    catch(error) {

        console.warn(
            "Reverse geocoding failed:",
            error
        );


        return "Selected Location";

    }

}


// ============================================================
// MAP CLICK
// ============================================================

map.on(

    "click",

    async function(event) {


        var latitude =
            event.latlng.lat;


        var longitude =
            event.latlng.lng;


        if (

            !isInsidePrototypeRegion(
                latitude,
                longitude
            )

        ) {

            showOutsideCoverage(
                latitude,
                longitude
            );


            return;

        }


        // Immediate UI response while reverse geocoding.
        showPredictionLoading(
            latitude,
            longitude
        );


        var locationName =
            await getLocationName(
                latitude,
                longitude
            );


        requestAeroVisionPrediction(

            latitude,

            longitude,

            locationName

        );

    }

);


// ============================================================
// RESET DEMO
// ============================================================

function resetAeroVisionDemo() {

    console.log(
        "🏠 Resetting AeroVision demo..."
    );


    hidePredictionPipeline();


    if (
        predictionMarker
    ) {

        map.removeLayer(
            predictionMarker
        );


        predictionMarker =
            null;

    }


    map.closePopup();


    map.setView(

        [
            22.5,
            79.0
        ],

        5,

        {
            animate:
                true
        }

    );


    // CPCB ON
    if (
        !map.hasLayer(
            cpcbLayer
        )
    ) {

        cpcbLayer.addTo(
            map
        );

    }


    // Other layers OFF
    [

        aqiSurfaceLayer,

        hchoLayer,

        fireLayer,

        windLayer

    ]

    .forEach(

        function(layer) {

            if (
                map.hasLayer(
                    layer
                )
            ) {

                map.removeLayer(
                    layer
                );

            }

        }

    );


    document
    .querySelectorAll(
        ".layer-button"
    )
    .forEach(

        function(button) {

            if (
                button.id !==
                "btn-demo-reset"
            ) {

                button.classList.remove(
                    "active"
                );

            }

        }

    );


    var cpcbButton =
        document.getElementById(
            "btn-cpcb"
        );


    if (
        cpcbButton
    ) {

        cpcbButton.classList.add(
            "active"
        );

    }


    setText(
        "selectedStation",
        "Select a location"
    );


    setText(
        "selectedCpcbAqi",
        "--"
    );


    setText(
        "selectedAeroAqi",
        "--"
    );


    setText(
        "selectedAqiError",
        "--"
    );


    setText(
        "selectedLocationName",
        "Click a CPCB station or map location"
    );


    setText(
        "selectedLocationDate",
        "--"
    );


    setText(
        "selectedCpcbCategory",
        "--"
    );


    setText(
        "selectedAeroCategory",
        "--"
    );


    setText(
        "selectedDominant",
        "--"
    );


    resetSelectedPollutants(
        "--"
    );


    if (

        prototypeRegion

        &&

        !map.hasLayer(
            prototypeRegion
        )

    ) {

        prototypeRegion.addTo(
            map
        );

    }


    console.log(
        "✅ AeroVision demo reset complete"
    );

}


// ============================================================
// FINISHED
// ============================================================

console.log(
    "✅ AeroVision smooth AQI dashboard initialized"
);