document.addEventListener('DOMContentLoaded', function () {
	// Получаем все флеш-сообщения, кроме сообщений об участии в квизе
	const flashMessages = document.querySelectorAll('.flash-message:not(.quiz-participation-message)');

	// Устанавливаем время автоматического скрытия
	const displayTime = 5000; // 5 секунд

	flashMessages.forEach(function (flash) {
		// Создаем Bootstrap Alert объект
		const bsAlert = new bootstrap.Alert(flash);

		// Устанавливаем таймер для автоматического скрытия
		setTimeout(function () {
			bsAlert.close();
		}, displayTime);

		// Останавливаем таймер при наведении мыши
		flash.addEventListener('mouseenter', function () {
			clearTimeout(flash.dataset.timeoutId);
		});

		// Возобновляем таймер при уходе мыши
		flash.addEventListener('mouseleave', function () {
			flash.dataset.timeoutId = setTimeout(function () {
				bsAlert.close();
			}, displayTime);
		});
	});
}); 