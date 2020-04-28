$(document).ready(function () {
	var table = $('#dataTable').DataTable({
		"bSort": false,
		"bInfo": false,
		"bPaginate": false,
		"searching": true,
		"columnDefs": [
		],
	});

	var toggle = false;

	var toggleFunc = function () {
		toggle = !toggle;

		$.fn.dataTable.ext.search.push(
			function (settings, data, dataIndex) {
				if (!toggle) return true;
				else {
					let x = table.cell(dataIndex, 0).data()[0];
					let y = isNaN(x);
					return isNaN(table.cell(dataIndex, 0).data()[0]);
				}
			}
		);
		table.draw();
	}

	toggleFunc();

	$("#toggle").click(function () {
		if (!toggle) this.innerHTML = 'Show Lots';
		else this.innerHTML = 'Hide Lots';

		toggleFunc();
	});
});