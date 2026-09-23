// ============================================================
// AEROVISION INDIA
// LANDING DASHBOARD
//
// DATA SOURCE:
// /data/exports/dashboard_june_2026.json
//
// REAL DATA ONLY
// ============================================================


let dashboardRecords = [];

let allStations = [];

let currentStation = null;

let currentDate = "2026-06-08";

let currentDataView = "AQI";


// ============================================================
// DATA VIEW CONFIG
// ============================================================

const DATA_VIEW_CONFIG = {

    PM25: {

        title: "PM2.5",

        observed: "PM25",

        predicted: "PRED_PM25",

        unit: "µg/m³"

    },


    PM10: {

        title: "PM10",

        observed: "PM10",

        predicted: "PRED_PM10",

        unit: "µg/m³"

    },


    NO2: {

        title: "NO₂",

        observed: "NO2",

        predicted: "PRED_NO2",

        unit: "µg/m³"

    },


    O3: {

        title: "O₃ 8H",

        observed: "O3_8H",

        predicted: "PRED_O3_8H",

        unit: "µg/m³"

    }

};


// ============================================================
// HELPERS
// ============================================================

function validNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return false;

    }


    const number =
        Number(value);


    return Number.isFinite(
        number
    );

}


function formatNumber(
    value,
    digits = 1
) {

    if (
        !validNumber(value)
    ) {

        return "N/A";

    }


    return Number(
        value
    ).toFixed(
        digits
    );

}


function setText(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (element) {

        element.textContent =
            value;

    }

}


function formatDate(
    dateText
) {

    if (!dateText) {

        return "N/A";

    }


    const parts =
        String(
            dateText
        ).split("-");


    if (
        parts.length !== 3
    ) {

        return dateText;

    }


    return (
        parts[2]
        +
        " June "
        +
        parts[0]
    );

}


// ============================================================
// AQI CATEGORY CLASS
// ============================================================

function categoryClass(
    category
) {

    const value =
        String(
            category || ""
        )
        .trim()
        .toLowerCase();


    if (
        value === "good"
    ) {

        return "timeline-good";

    }


    if (
        value === "satisfactory"
    ) {

        return "timeline-satisfactory";

    }


    if (
        value === "moderate"
    ) {

        return "timeline-moderate";

    }


    if (
        value === "poor"
    ) {

        return "timeline-poor";

    }


    if (
        value === "very poor"
    ) {

        return "timeline-very-poor";

    }


    if (
        value === "severe"
    ) {

        return "timeline-severe";

    }


    return "";

}


// ============================================================
// HERO AQI THEME
// ============================================================

function setHeroTheme(
    category
) {

    const hero =
        document.getElementById(
            "aqiHero"
        );


    const number =
        document.getElementById(
            "heroAeroAQI"
        );


    if (
        !hero ||
        !number
    ) {

        return;

    }


    const value =
        String(
            category || ""
        )
        .trim()
        .toLowerCase();


    let background =
        "linear-gradient(135deg,#fffdf3,#fff0a7)";

    let border =
        "#f3df88";

    let numberColor =
        "#dba900";


    if (
        value === "good"
    ) {

        background =
            "linear-gradient(135deg,#f1fff4,#ccefd3)";

        border =
            "#a7dfb4";

        numberColor =
            "#139548";

    }


    else if (
        value === "satisfactory"
    ) {

        background =
            "linear-gradient(135deg,#fbffef,#e8f3b7)";

        border =
            "#d4e48c";

        numberColor =
            "#809f20";

    }


    else if (
        value === "moderate"
    ) {

        background =
            "linear-gradient(135deg,#fffdf3,#fff0a7)";

        border =
            "#f3df88";

        numberColor =
            "#dba900";

    }


    else if (
        value === "poor"
    ) {

        background =
            "linear-gradient(135deg,#fff9f0,#ffd6a5)";

        border =
            "#f3b76f";

        numberColor =
            "#df7610";

    }


    else if (
        value === "very poor"
    ) {

        background =
            "linear-gradient(135deg,#fff3f3,#f6bdbd)";

        border =
            "#eca3a3";

        numberColor =
            "#c83f3f";

    }


    else if (
        value === "severe"
    ) {

        background =
            "linear-gradient(135deg,#faeff4,#ddb6c5)";

        border =
            "#cc97ad";

        numberColor =
            "#84284d";

    }


    hero.style.background =
        background;


    hero.style.borderColor =
        border;


    number.style.color =
        numberColor;

}


// ============================================================
// STATION ROWS
// ============================================================

function getStationRows() {

    return dashboardRecords

        .filter(

            row =>
                row.station ===
                currentStation

        )

        .sort(

            (a, b) =>
                a.date.localeCompare(
                    b.date
                )

        );

}


// ============================================================
// CURRENT RECORD
// ============================================================

function getCurrentRecord() {

    return dashboardRecords.find(

        row =>

            row.station ===
            currentStation

            &&

            row.date ===
            currentDate

    );

}


// ============================================================
// NEAREST AVAILABLE DATE
// ============================================================

function findAvailableDateForStation(
    preferredDate
) {

    const stationRows =
        getStationRows();


    if (
        stationRows.length === 0
    ) {

        return null;

    }


    const exact =
        stationRows.find(

            row =>
                row.date ===
                preferredDate

        );


    if (exact) {

        return exact.date;

    }


    const preferredDay =
        Number(
            preferredDate.slice(
                -2
            )
        );


    let bestRow =
        stationRows[0];

    let bestDistance =
        999;


    stationRows.forEach(

        row => {

            const rowDay =
                Number(
                    row.date.slice(
                        -2
                    )
                );


            const distance =
                Math.abs(
                    rowDay -
                    preferredDay
                );


            if (
                distance <
                bestDistance
            ) {

                bestDistance =
                    distance;

                bestRow =
                    row;

            }

        }

    );


    return bestRow.date;

}


// ============================================================
// MAIN DASHBOARD UPDATE
// ============================================================

function updateDashboard() {

    const row =
        getCurrentRecord();


    if (!row) {

        console.warn(
            "No record:",
            currentStation,
            currentDate
        );

        return;

    }


    // ========================================================
    // LOCATION
    // ========================================================

    setText(
        "heroStation",
        row.station || "N/A"
    );


    const locationParts =
        [
            row.city,
            row.state
        ]
        .filter(

            value =>
                value &&
                value !== "nan" &&
                value !== "None"

        );


    setText(

        "heroLocation",

        locationParts.length

            ?

            locationParts.join(
                ", "
            )

            :

            "CPCB monitoring station"

    );


    // ========================================================
    // DATE
    // ========================================================

    setText(
        "heroDate",
        formatDate(
            row.date
        )
    );


    setText(
        "timelineSelectedDate",
        formatDate(
            row.date
        )
    );


    setText(
        "tableDateLabel",
        "Station records · "
        +
        formatDate(
            row.date
        )
    );


    setText(
        "chartStationName",
        row.station
    );


    setText(

        "datasetDate",

        "Selected observation: "
        +
        formatDate(
            row.date
        )
        +
        " · Real June 2026 station-day dataset"

    );


    // ========================================================
    // MODEL PERIOD
    // ========================================================

    if (
        row.model_period ===
        "HELD_OUT_VALIDATION"
    ) {

        setText(
            "heroPeriodLabel",
            "Held-out validation"
        );

    }

    else {

        setText(
            "heroPeriodLabel",
            "Training-period estimate"
        );

    }


    // ========================================================
    // POLLUTANT CARDS
    // CPCB
    // ========================================================

    setText(
        "cardPM25",
        formatNumber(
            row.PM25,
            1
        )
    );


    setText(
        "cardPM10",
        formatNumber(
            row.PM10,
            1
        )
    );


    setText(
        "cardNO2",
        formatNumber(
            row.NO2,
            1
        )
    );


    setText(
        "cardO3",
        formatNumber(
            row.O3_8H,
            1
        )
    );


    // ========================================================
    // POLLUTANT CARDS
    // AEROVISION
    // ========================================================

    setText(
        "cardPredPM25",
        formatNumber(
            row.PRED_PM25,
            1
        )
    );


    setText(
        "cardPredPM10",
        formatNumber(
            row.PRED_PM10,
            1
        )
    );


    setText(
        "cardPredNO2",
        formatNumber(
            row.PRED_NO2,
            1
        )
    );


    setText(
        "cardPredO3",
        formatNumber(
            row.PRED_O3_8H,
            1
        )
    );


    // ========================================================
    // ENVIRONMENTAL VALUES
    // ========================================================

    setText(
        "envAOD",
        formatNumber(
            row.AOD,
            3
        )
    );


    setText(

        "envAODStatus",

        validNumber(
            row.AOD
        )

            ?

            "MODIS MAIAC"

            :

            "No valid pixel"

    );


    setText(
        "envHCHO",
        formatNumber(
            row.HCHO,
            6
        )
    );


    setText(
        "envSatNO2",
        formatNumber(
            row.SAT_NO2,
            6
        )
    );


    setText(

        "envTemp",

        validNumber(
            row.ERA5_TEMP
        )

            ?

            formatNumber(
                row.ERA5_TEMP,
                1
            )
            +
            " °C"

            :

            "N/A"

    );


    setText(

        "envRH",

        validNumber(
            row.ERA5_RH
        )

            ?

            formatNumber(
                row.ERA5_RH,
                1
            )
            +
            " %"

            :

            "N/A"

    );


    setText(

        "envWind",

        validNumber(
            row.WIND_SPEED
        )

            ?

            formatNumber(
                row.WIND_SPEED,
                2
            )
            +
            " m/s"

            :

            "N/A"

    );


    setText(

        "envFire",

        validNumber(
            row.FIRE_COUNT_25KM
        )

            ?

            formatNumber(
                row.FIRE_COUNT_25KM,
                0
            )

            :

            "N/A"

    );


    // ========================================================
    // TIMELINE / TABLE
    // ========================================================

    renderTimeline();

    renderTimelineChart();

    renderStationTable();


    // ========================================================
    // HERO MODE
    // ========================================================

    renderHeroForCurrentView();


    // ========================================================
    // SPECIFIC POLLUTANT PANEL
    // ========================================================

    if (
        currentDataView !== "AQI" &&
        currentDataView !== "HISTORY"
    ) {

        renderSpecificData();

    }

}


// ============================================================
// HERO SWITCHER
// ============================================================

function renderHeroForCurrentView() {

    const row =
        getCurrentRecord();


    if (!row) {

        return;

    }


    const aeroLabel =
        document.querySelector(
            ".aqi-label"
        );


    const references =
        document.querySelectorAll(
            ".reference-item span"
        );


    // ========================================================
    // AQI MODE / HISTORY MODE
    // ========================================================

    if (
        currentDataView === "AQI" ||
        currentDataView === "HISTORY"
    ) {

        if (aeroLabel) {

            aeroLabel.textContent =
                "AeroVision AQI";

        }


        if (
            references[0]
        ) {

            references[0].textContent =
                "CPCB AQI";

        }


        if (
            references[1]
        ) {

            references[1].textContent =
                "AQI Difference";

        }


        setText(
            "heroAeroAQI",
            formatNumber(
                row.AEROVISION_AQI,
                0
            )
        );


        setText(
            "heroAeroCategory",
            row.AEROVISION_CATEGORY ||
            "N/A"
        );


        setText(
            "heroCpcbAQI",
            formatNumber(
                row.CPCB_AQI,
                0
            )
        );


        setText(
            "heroCpcbCategory",
            row.CPCB_CATEGORY ||
            "N/A"
        );


        if (
            row.CPCB_REFERENCE_STATUS === "FULL" &&
            validNumber(
                row.AQI_ERROR
            )
        ) {

            setText(
                "heroDifference",
                formatNumber(
                    row.AQI_ERROR,
                    1
                )
            );


            setText(
                "heroReferenceStatus",
                "Full CPCB reference"
            );

        }

        else {

            setText(
                "heroDifference",
                "N/A"
            );


            setText(

                "heroReferenceStatus",

                "Partial CPCB reference ("
                +
                (
                    row.CPCB_VALID_POLLUTANTS ??
                    0
                )
                +
                "/4)"

            );

        }


        setHeroTheme(
            row.AEROVISION_CATEGORY
        );


        return;

    }


    // ========================================================
    // POLLUTANT MODE
    // ========================================================

    const config =
        DATA_VIEW_CONFIG[
            currentDataView
        ];


    if (!config) {

        return;

    }


    const observed =
        row[
            config.observed
        ];


    const predicted =
        row[
            config.predicted
        ];


    // ========================================================
    // LABELS
    // ========================================================

    if (aeroLabel) {

        aeroLabel.textContent =
            "AeroVision "
            +
            config.title;

    }


    if (
        references[0]
    ) {

        references[0].textContent =
            "CPCB "
            +
            config.title;

    }


    if (
        references[1]
    ) {

        references[1].textContent =
            "Difference";

    }


    // ========================================================
    // AEROVISION VALUE
    // ========================================================

    setText(

        "heroAeroAQI",

        validNumber(
            predicted
        )

            ?

            formatNumber(
                predicted,
                1
            )

            :

            "N/A"

    );


    // Category badge becomes unit

    setText(
        "heroAeroCategory",
        config.unit
    );


    // ========================================================
    // CPCB VALUE
    // ========================================================

    setText(

        "heroCpcbAQI",

        validNumber(
            observed
        )

            ?

            formatNumber(
                observed,
                1
            )

            :

            "N/A"

    );


    setText(
        "heroCpcbCategory",
        config.unit
    );


    // ========================================================
    // DIFFERENCE
    // ========================================================

    if (
        validNumber(
            observed
        ) &&
        validNumber(
            predicted
        )
    ) {

        const difference =
            Math.abs(

                Number(
                    observed
                )

                -

                Number(
                    predicted
                )

            );


        setText(
            "heroDifference",
            difference.toFixed(
                1
            )
        );


        setText(
            "heroReferenceStatus",
            config.unit
        );

    }

    else {

        setText(
            "heroDifference",
            "N/A"
        );


        setText(
            "heroReferenceStatus",
            "Observation unavailable"
        );

    }


    // ========================================================
    // POLLUTANT HERO COLOR
    // ========================================================

    const hero =
        document.getElementById(
            "aqiHero"
        );


    const heroNumber =
        document.getElementById(
            "heroAeroAQI"
        );


    if (hero) {

        hero.style.background =
            "linear-gradient(135deg,#f4fbff,#dcefff)";


        hero.style.borderColor =
            "#acd8f5";

    }


    if (heroNumber) {

        heroNumber.style.color =
            "#1687e6";

    }

}


// ============================================================
// STATION SELECTOR
// ============================================================

function buildStationSelector() {

    const selector =
        document.getElementById(
            "stationSelector"
        );


    if (!selector) {

        return;

    }


    selector.innerHTML =
        "";


    allStations.forEach(

        station => {

            const stationRows =
                dashboardRecords.filter(

                    row =>
                        row.station ===
                        station

                );


            const sample =
                stationRows[0];


            const option =
                document.createElement(
                    "option"
                );


            option.value =
                station;


            let label =
                station;


            if (
                sample &&
                sample.city &&
                sample.city !== "nan"
            ) {

                label +=
                    " · "
                    +
                    sample.city;

            }


            option.textContent =
                label;


            selector.appendChild(
                option
            );

        }

    );


    const preferredStation =
        allStations.find(

            station =>
                station
                .toLowerCase()
                .includes(
                    "alipur"
                )

        );


    currentStation =
        preferredStation ||
        allStations[0];


    selector.value =
        currentStation;


    selector.addEventListener(

        "change",

        function() {

            currentStation =
                selector.value;


            const availableDate =
                findAvailableDateForStation(
                    currentDate
                );


            if (availableDate) {

                currentDate =
                    availableDate;

            }


            updateDashboard();

        }

    );

}


// ============================================================
// JUNE TIMELINE
// ============================================================

function renderTimeline() {

    const container =
        document.getElementById(
            "juneTimeline"
        );


    if (!container) {

        return;

    }


    container.innerHTML =
        "";


    const stationRows =
        getStationRows();


    for (
        let day = 1;
        day <= 30;
        day++
    ) {

        const date =
            "2026-06-"
            +
            String(day).padStart(
                2,
                "0"
            );


        const row =
            stationRows.find(

                item =>
                    item.date ===
                    date

            );


        const button =
            document.createElement(
                "button"
            );


        button.type =
            "button";


        button.className =
            "timeline-day";


        if (
            date ===
            currentDate
        ) {

            button.classList.add(
                "active"
            );

        }


        if (row) {

            const cssCategory =
                categoryClass(
                    row.AEROVISION_CATEGORY
                );


            if (cssCategory) {

                button.classList.add(
                    cssCategory
                );

            }


            const aeroText =
                validNumber(
                    row.AEROVISION_AQI
                )

                    ?

                    Math.round(
                        Number(
                            row.AEROVISION_AQI
                        )
                    )

                    :

                    "N/A";


            const cpcbText =
                validNumber(
                    row.CPCB_AQI
                )

                    ?

                    Math.round(
                        Number(
                            row.CPCB_AQI
                        )
                    )

                    :

                    "N/A";


            button.innerHTML = `

                <span class="day-number">
                    ${String(day).padStart(2,"0")}
                </span>

                <span class="day-aqi">
                    AI ${aeroText}
                </span>

                <span class="day-cpcb">
                    CPCB ${cpcbText}
                </span>

            `;


            button.title =
                formatDate(
                    date
                )
                +
                "\nAeroVision AQI: "
                +
                aeroText
                +
                "\nCPCB AQI: "
                +
                cpcbText;


            button.addEventListener(

                "click",

                function() {

                    currentDate =
                        date;


                    updateDashboard();

                }

            );

        }

        else {

            button.classList.add(
                "no-data"
            );


            button.disabled =
                true;


            button.innerHTML = `

                <span class="day-number">
                    ${String(day).padStart(2,"0")}
                </span>

                <span class="day-aqi">
                    N/A
                </span>

                <span class="day-cpcb">
                    No record
                </span>

            `;


            button.title =
                "No real station-day record available";

        }


        container.appendChild(
            button
        );

    }

}


// ============================================================
// FULL JUNE AQI CHART
// ============================================================

function renderTimelineChart() {

    const chart =
        document.getElementById(
            "aqiTimelineChart"
        );


    if (!chart) {

        return;

    }


    chart.innerHTML =
        "";


    const stationRows =
        getStationRows();


    const maxAQI =
        500;


    for (
        let day = 1;
        day <= 30;
        day++
    ) {

        const date =
            "2026-06-"
            +
            String(day).padStart(
                2,
                "0"
            );


        const row =
            stationRows.find(

                item =>
                    item.date ===
                    date

            );


        const dayContainer =
            document.createElement(
                "div"
            );


        dayContainer.className =
            "timeline-chart-day";


        if (row) {

            // CPCB

            if (
                validNumber(
                    row.CPCB_AQI
                )
            ) {

                const cpcbValue =
                    Math.min(
                        maxAQI,
                        Number(
                            row.CPCB_AQI
                        )
                    );


                const cpcbBar =
                    document.createElement(
                        "div"
                    );


                cpcbBar.className =
                    "timeline-bar timeline-bar-cpcb";


                cpcbBar.style.height =
                    (
                        cpcbValue /
                        maxAQI *
                        100
                    )
                    +
                    "%";


                cpcbBar.title =
                    formatDate(
                        date
                    )
                    +
                    "\nCPCB AQI: "
                    +
                    Math.round(
                        Number(
                            row.CPCB_AQI
                        )
                    );


                dayContainer.appendChild(
                    cpcbBar
                );

            }


            // AeroVision

            if (
                validNumber(
                    row.AEROVISION_AQI
                )
            ) {

                const aeroValue =
                    Math.min(
                        maxAQI,
                        Number(
                            row.AEROVISION_AQI
                        )
                    );


                const aeroBar =
                    document.createElement(
                        "div"
                    );


                aeroBar.className =
                    "timeline-bar timeline-bar-aero";


                aeroBar.style.height =
                    (
                        aeroValue /
                        maxAQI *
                        100
                    )
                    +
                    "%";


                aeroBar.title =
                    formatDate(
                        date
                    )
                    +
                    "\nAeroVision AQI: "
                    +
                    Math.round(
                        Number(
                            row.AEROVISION_AQI
                        )
                    );


                dayContainer.appendChild(
                    aeroBar
                );

            }

        }


        const label =
            document.createElement(
                "span"
            );


        label.className =
            "timeline-chart-label";


        label.textContent =
            day;


        dayContainer.appendChild(
            label
        );


        chart.appendChild(
            dayContainer
        );

    }

}


// ============================================================
// STATION TABLE
// ============================================================

function renderStationTable() {

    const body =
        document.getElementById(
            "stationTableBody"
        );


    if (!body) {

        return;

    }


    body.innerHTML =
        "";


    const rows =
        dashboardRecords

        .filter(

            row =>
                row.date ===
                currentDate

        )

        .sort(

            (a, b) =>
                a.station.localeCompare(
                    b.station
                )

        );


    if (
        rows.length === 0
    ) {

        const tr =
            document.createElement(
                "tr"
            );


        tr.innerHTML = `

            <td colspan="9">
                No real station records available for
                ${formatDate(currentDate)}.
            </td>

        `;


        body.appendChild(
            tr
        );


        return;

    }


    rows.forEach(

        row => {

            const tr =
                document.createElement(
                    "tr"
                );


            if (
                row.station ===
                currentStation
            ) {

                tr.classList.add(
                    "selected-row"
                );

            }


            let location =
                [
                    row.city,
                    row.state
                ]
                .filter(

                    value =>
                        value &&
                        value !== "nan"

                )
                .join(
                    ", "
                );


            if (!location) {

                location =
                    "N/A";

            }


            tr.innerHTML = `

                <td>
                    <strong>
                        ${row.station || "N/A"}
                    </strong>
                </td>

                <td>
                    ${location}
                </td>

                <td>
                    ${formatNumber(row.CPCB_AQI,0)}
                </td>

                <td>
                    ${formatNumber(row.AEROVISION_AQI,0)}
                </td>

                <td>
                    ${row.AEROVISION_CATEGORY || "N/A"}
                </td>

                <td>
                    ${formatNumber(row.PM25,1)}
                </td>

                <td>
                    ${formatNumber(row.PM10,1)}
                </td>

                <td>
                    ${formatNumber(row.NO2,1)}
                </td>

                <td>
                    ${formatNumber(row.O3_8H,1)}
                </td>

            `;


            tr.addEventListener(

                "click",

                function() {

                    currentStation =
                        row.station;


                    const selector =
                        document.getElementById(
                            "stationSelector"
                        );


                    if (selector) {

                        selector.value =
                            currentStation;

                    }


                    updateDashboard();


                    window.scrollTo({

                        top:
                            0,

                        behavior:
                            "smooth"

                    });

                }

            );


            body.appendChild(
                tr
            );

        }

    );

}


// ============================================================
// DATA VIEW TAB EVENTS
// ============================================================

function initializeDataViewButtons() {

    document
    .querySelectorAll(
        ".data-view-btn"
    )
    .forEach(

        button => {

            button.addEventListener(

                "click",

                function() {

                    document
                    .querySelectorAll(
                        ".data-view-btn"
                    )
                    .forEach(

                        item => {

                            item.classList.remove(
                                "active"
                            );

                        }

                    );


                    button.classList.add(
                        "active"
                    );


                    currentDataView =
                        button.dataset.view;


                    handleDataView();

                }

            );

        }

    );

}


// ============================================================
// HANDLE DATA VIEW
// ============================================================

function handleDataView() {

    const panel =
        document.getElementById(
            "specificDataPanel"
        );


    // ========================================================
    // AQI
    // ========================================================

    if (
        currentDataView === "AQI"
    ) {

        if (panel) {

            panel.hidden =
                true;

        }


        renderHeroForCurrentView();

        return;

    }


    // ========================================================
    // HISTORY
    // ========================================================

    if (
        currentDataView === "HISTORY"
    ) {

        if (panel) {

            panel.hidden =
                true;

        }


        renderHeroForCurrentView();


        const history =
            document.getElementById(
                "history"
            );


        if (history) {

            history.scrollIntoView({

                behavior:
                    "smooth",

                block:
                    "start"

            });

        }


        return;

    }


    // ========================================================
    // POLLUTANT
    // ========================================================

    if (panel) {

        panel.hidden =
            false;

    }


    renderHeroForCurrentView();

    renderSpecificData();

}


// ============================================================
// SPECIFIC POLLUTANT DETAILS
// ============================================================

function renderSpecificData() {

    const config =
        DATA_VIEW_CONFIG[
            currentDataView
        ];


    if (!config) {

        return;

    }


    const row =
        getCurrentRecord();


    if (!row) {

        return;

    }


    const observed =
        row[
            config.observed
        ];


    const predicted =
        row[
            config.predicted
        ];


    setText(
        "specificDataTitle",
        config.title
    );


    setText(
        "specificHistoryTitle",
        config.title
        +
        " · June 2026 History"
    );


    setText(
        "specificStationName",
        row.station
    );


    setText(
        "specificDataDate",
        formatDate(
            row.date
        )
    );


    setText(
        "specificCPCB",
        formatNumber(
            observed,
            1
        )
    );


    setText(
        "specificAero",
        formatNumber(
            predicted,
            1
        )
    );


    setText(
        "specificUnitCPCB",
        config.unit
    );


    setText(
        "specificUnitAero",
        config.unit
    );


    if (
        validNumber(
            observed
        )
        &&
        validNumber(
            predicted
        )
    ) {

        setText(

            "specificDifference",

            Math.abs(

                Number(
                    observed
                )

                -

                Number(
                    predicted
                )

            ).toFixed(
                1
            )

        );

    }

    else {

        setText(
            "specificDifference",
            "N/A"
        );

    }


    setText(
        "specificDay",
        Number(
            row.date.slice(
                -2
            )
        )
    );


    renderSpecificHistoryChart(
        config
    );

}


// ============================================================
// SPECIFIC POLLUTANT HISTORY
// ============================================================

function renderSpecificHistoryChart(
    config
) {

    const chart =
        document.getElementById(
            "specificHistoryChart"
        );


    if (!chart) {

        return;

    }


    chart.innerHTML =
        "";


    const rows =
        getStationRows();


    const values =
        [];


    rows.forEach(

        row => {

            if (
                validNumber(
                    row[
                        config.observed
                    ]
                )
            ) {

                values.push(

                    Number(
                        row[
                            config.observed
                        ]
                    )

                );

            }


            if (
                validNumber(
                    row[
                        config.predicted
                    ]
                )
            ) {

                values.push(

                    Number(
                        row[
                            config.predicted
                        ]
                    )

                );

            }

        }

    );


    const maximum =
        Math.max(
            1,
            ...values
        );


    for (
        let day = 1;
        day <= 30;
        day++
    ) {

        const date =
            "2026-06-"
            +
            String(day).padStart(
                2,
                "0"
            );


        const row =
            rows.find(

                item =>
                    item.date ===
                    date

            );


        const holder =
            document.createElement(
                "div"
            );


        holder.className =
            "specific-history-day";


        if (row) {

            const cpcb =
                row[
                    config.observed
                ];


            const aero =
                row[
                    config.predicted
                ];


            // =================================================
            // CPCB BAR
            // =================================================

            if (
                validNumber(
                    cpcb
                )
            ) {

                const bar =
                    document.createElement(
                        "div"
                    );


                bar.className =
                    "specific-history-bar cpcb";


                bar.style.height =

                    (
                        Number(cpcb)
                        /
                        maximum
                        *
                        100
                    )

                    +
                    "%";


                bar.title =

                    formatDate(date)

                    +

                    "\nCPCB "

                    +

                    config.title

                    +

                    ": "

                    +

                    formatNumber(
                        cpcb,
                        1
                    )

                    +

                    " "

                    +

                    config.unit;


                holder.appendChild(
                    bar
                );

            }


            // =================================================
            // AEROVISION BAR
            // =================================================

            if (
                validNumber(
                    aero
                )
            ) {

                const bar =
                    document.createElement(
                        "div"
                    );


                bar.className =
                    "specific-history-bar aero";


                bar.style.height =

                    (
                        Number(aero)
                        /
                        maximum
                        *
                        100
                    )

                    +

                    "%";


                bar.title =

                    formatDate(date)

                    +

                    "\nAeroVision "

                    +

                    config.title

                    +

                    ": "

                    +

                    formatNumber(
                        aero,
                        1
                    )

                    +

                    " "

                    +

                    config.unit;


                holder.appendChild(
                    bar
                );

            }

        }


        const label =
            document.createElement(
                "span"
            );


        label.className =
            "specific-history-label";


        label.textContent =
            day;


        holder.appendChild(
            label
        );


        chart.appendChild(
            holder
        );

    }

}


// ============================================================
// LOAD DASHBOARD DATA
// ============================================================

async function loadDashboardData() {

    try {

        const response =
            await fetch(

                "/data/exports/dashboard_june_2026.json",

                {
                    cache:
                        "no-store"
                }

            );


        if (
            !response.ok
        ) {

            throw new Error(

                "Unable to load June dashboard dataset. HTTP "

                +

                response.status

            );

        }


        const data =
            await response.json();


        if (
            !Array.isArray(
                data.records
            )
        ) {

            throw new Error(
                "dashboard_june_2026.json has no records array."
            );

        }


        dashboardRecords =
            data.records;


        if (
            dashboardRecords.length === 0
        ) {

            throw new Error(
                "June dashboard dataset contains no records."
            );

        }


        allStations =
            Array.isArray(
                data.stations
            )

                ?

                data.stations

                :

                [
                    ...new Set(

                        dashboardRecords.map(

                            row =>
                                row.station

                        )

                    )
                ];


        allStations =
            allStations

            .filter(
                Boolean
            )

            .sort(

                (a, b) =>
                    a.localeCompare(
                        b
                    )

            );


        console.log(
            "AeroVision records:",
            dashboardRecords.length
        );


        console.log(
            "Stations:",
            allStations.length
        );


        console.log(
            "Dataset:",
            data.date_start,
            "to",
            data.date_end
        );


        // ====================================================
        // SELECTOR
        // ====================================================

        buildStationSelector();


        // ====================================================
        // DEFAULT DATE
        // ====================================================

        currentDate =
            "2026-06-08";


        const availableDate =
            findAvailableDateForStation(
                currentDate
            );


        if (availableDate) {

            currentDate =
                availableDate;

        }


        // ====================================================
        // INITIALIZE TABS
        // ====================================================

        initializeDataViewButtons();


        // ====================================================
        // INITIAL RENDER
        // ====================================================

        updateDashboard();


        console.log(
            "✅ AeroVision June dashboard ready"
        );

    }

    catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );


        setText(
            "heroStation",
            "Dataset unavailable"
        );


        setText(
            "datasetDate",
            error.message
        );


        setText(
            "heroAeroAQI",
            "N/A"
        );


        setText(
            "heroCpcbAQI",
            "N/A"
        );


        setText(
            "heroDifference",
            "N/A"
        );


        setText(
            "envAOD",
            "N/A"
        );


        setText(
            "envHCHO",
            "N/A"
        );


        setText(
            "envSatNO2",
            "N/A"
        );


        setText(
            "envTemp",
            "N/A"
        );


        setText(
            "envRH",
            "N/A"
        );


        setText(
            "envWind",
            "N/A"
        );


        setText(
            "envFire",
            "N/A"
        );

    }

}


// ============================================================
// INITIALIZE
// ============================================================

loadDashboardData();