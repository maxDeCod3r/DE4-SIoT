var timestamps = []
var temperatures = []
var humidities = []
var winds = []
var precipitations = []
var clouds = []
var stemps = []
var shmdts = []
var datetimes = []
var formatted_datetimes = []
var test_1 = [1, 2, 3, 4, 5, 6, 7]
var test_2 = [1, 2, 3, 4, 5, 6, 7]
let data_lim = 2
    // let data_lim = 240

async function get_all_data() {
    let database = firebase.firestore()
    let weather_data = database.collection("weather_data")
    console.log("Waiting for data...");
    var data_snapshot = await weather_data.orderBy("timestamp", "desc").limit(data_lim).get()
    console.log("Got data, Processing...");
    data_snapshot.forEach((data_slice) => {
        var slice = data_slice.data()
        timestamps.push(slice.timestamp)
        datetimes.push(slice.datetime)
        formatted_datetimes.push(slice.datetime.toDate())
        temperatures.push(slice.temp)
        humidities.push(slice.humidity)
        winds.push(slice.wind)
        precipitations.push(slice.rain_1h)
        clouds.push(slice.cloud)
        stemps.push(slice.local_soil_temperature)
        shmdts.push(slice.local_soil_humidity)
    })
    console.log("Added all data...");
}

function draw_graph(ySeries, names, colors, div_name) {
    var trace = {
        type: ySeries.type,
        y: ySeries.data,
        x: formatted_datetimes,
        text: names.title,
        line: { shape: 'spline' },
        // marker: { color: colors.trace, line: { width: 3 } }
        marker: { color: colors.trace, line: { color: colors.trace, width: 3 } }
    }
    var data = [trace]

    var layout = {
        font: { size: 15, color: '#AAAAAA' },
        paper_bgcolor: '#111111',
        plot_bgcolor: '#111111',
        title: { text: names.title, font: { color: '#FFFFFF' } },
        xaxis: { title: { text: 'Date', font: { color: '#FFFFFF' } } },
        yaxis: { title: { text: names.yaxis, font: { color: '#FFFFFF' } } }
    }

    var config = { responsive: true, scrollZoom: false, displaylogo: false }

    Plotly.newPlot(div_name, data, layout, config)
}


async function plot_graphs() {
    await get_all_data()
    console.log("Starting data plot...");
    draw_graph({ data: temperatures, type: 'line' }, { title: "Air Temperature", yaxis: "Temperature in ºC" }, { trace: '#00FFFF' },
        'temp_chart'
    )
    draw_graph({ data: humidities, type: 'line' }, { title: "Humidity", yaxis: "Air humidity in %" }, { trace: '#00AAFF' },
        'humidity_chart'
    )
    draw_graph({ data: winds, type: 'line' }, { title: "Wind speed", yaxis: "Wind speed in m/s" }, { trace: '#AAFFAA' },
        'wind_chart'
    )
    draw_graph({ data: precipitations, type: 'bar' }, { title: "Precipitation", yaxis: "Rainfall in mm" }, { trace: '#FF3333' },
        'rain_chart'
    )
    draw_graph({ data: clouds, type: 'bar' }, { title: "Cloud cover", yaxis: "Cloud coverage in %" }, { trace: '#FFFFFF' },
        'cloud_chart'
    )
    draw_graph({ data: stemps, type: 'line' }, { title: "Soil temperature", yaxis: "Temperature in ºC" }, { trace: '#FF9966' },
        'soil_temp__chart'
    )
    draw_graph({ data: shmdts, type: 'line' }, { title: "Soil humidity", yaxis: "Humidity (0->3000)" }, { trace: '#9933FF' },
        'soil_hmdt_chart'
    )
}


function createGraph_2() {
    console.log(temperatures);
    var data = [{ type: "line", x: formatted_datetimes, y: temperatures }]
    var layout = { title: 'Graph 2', font: { size: 18 } }
    var config = { responsive: true }
    Plotly.newPlot('chart_2', data, layout, config)

}

plot_graphs();



// var counter = 0
// logRef.onSnapshot(function(querySnapshot) {
//     var updates = querySnapshot.docChanges()
//     if (updates.length < 5){
//         updates.forEach(function(change) {
//             var docData = change.doc.data()
//             Plotly.extendTraces('chart', {y:[[docData.value2]]}, [0])
//             counter++
//             if (counter > 50) {
//                 Plotly.relayout('chart', {
//                     xaxis: {
//                         range: [counter - 50, counter]
//                     }
//                 })
//             }
//         })
//     }
// })