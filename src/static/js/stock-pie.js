Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

var canvas = document.getElementById("myPieChart");
var ctx = canvas.getContext('2d');

var gradient = ctx.createLinearGradient(0, 0, 600, 0);

gradient.addColorStop(0, '#8360c3');
gradient.addColorStop(1, '#2ebf91');

var myPieChart = new Chart(canvas, {
	type: 'doughnut',
	data: {
		labels: pieLabels,
		datasets: [{
			data: pieData,
			backgroundColor: gradient,
			hoverBackgroundColor: gradient,
			hoverBorderColor: "rgba(234, 236, 244, 1)",
		}],
	},
	options: {
		maintainAspectRatio: false,
		tooltips: {
			backgroundColor: "rgb(255,255,255)",
			bodyFontColor: "#858796",
			borderColor: '#dddfeb',
			borderWidth: 1,
			xPadding: 15,
			yPadding: 15,
			displayColors: false,
			caretPadding: 10,
		},
		legend: {
			display: false
		},
		cutoutPercentage: 80,
	},
});