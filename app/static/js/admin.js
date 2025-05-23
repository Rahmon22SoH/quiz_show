// Убедитесь, что модальные окна инициализируются
document.addEventListener('DOMContentLoaded', function () {
	console.log('DOM loaded');

	// Логируем все модальные окна
	var modals = document.querySelectorAll('.modal');
	console.log('Found modals:', modals.length);

	// Логируем все кнопки, открывающие модальные окна
	var modalButtons = document.querySelectorAll('[data-bs-toggle="modal"]');
	console.log('Found modal buttons:', modalButtons.length);

	// Добавляем обработчик клика на все кнопки
	modalButtons.forEach(function (button) {
		console.log('Button target:', button.getAttribute('data-bs-target'));
		button.addEventListener('click', function () {
			console.log('Button clicked:', this.getAttribute('data-bs-target'));
		});
	});
}); 