var ctx = document.getElementById('chart1').getContext('2d');

console.log(chartData);

var color = Chart.helpers.color;
var cfg = {
	data: {
		datasets: [{
			label: ticker,
			backgroundColor: "rgba(78, 115, 223, 0.05)",
			borderColor: "rgba(78, 115, 223, 1)",
			data: chartData,
	type: 'line',
	pointRadius: 0,
	fill: false,
	lineTension: 0,
	borderWidth: 2
}]
	},
options: {
	legend: {
		display: false
	},
	animation: {
		duration: 0
	},
	scales: {
		xAxes: [{
			gridLines: {
				drawOnChartArea: false
			},
			type: 'time',
			distribution: 'series',
			offset: true,
			ticks: {
				major: {
					enabled: true,
					fontStyle: 'bold'
				},
				source: 'data',
				autoSkip: true,
				autoSkipPadding: 75,
				maxRotation: 0,
				sampleSize: 100
			},
			afterBuildTicks: function (scale, ticks) {
				var majorUnit = scale._majorUnit;
				var firstTick = ticks[0];
				var i, ilen, val, tick, currMajor, lastMajor;

				val = moment(ticks[0].value);
				if ((majorUnit === 'minute' && val.second() === 0)
					|| (majorUnit === 'hour' && val.minute() === 0)
					|| (majorUnit === 'day' && val.hour() === 9)
					|| (majorUnit === 'month' && val.date() <= 3 && val.isoWeekday() === 1)
					|| (majorUnit === 'year' && val.month() === 0)) {
					firstTick.major = true;
				} else {
					firstTick.major = false;
				}
				lastMajor = val.get(majorUnit);

				for (i = 1, ilen = ticks.length; i < ilen; i++) {
					tick = ticks[i];
					val = moment(tick.value);
					currMajor = val.get(majorUnit);
					tick.major = currMajor !== lastMajor;
					lastMajor = currMajor;
				}
				return ticks;
			}
		}],
			yAxes: [{
				gridLines: {
					drawOnChartArea: false
				},
			}]
	},
	tooltips: {
		intersect: false,
			mode: 'index',
				callbacks: {
			label: function (tooltipItem, myData) {
				var label = myData.datasets[tooltipItem.datasetIndex].label || '';
				if (label) {
					label += ': ';
				}
				label += parseFloat(tooltipItem.value).toFixed(2);
				return label;
			}
		}
	}
}
};

var chart = new Chart(ctx, cfg);