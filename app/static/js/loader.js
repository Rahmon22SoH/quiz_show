window.addEventListener('load', function () {
	var loader = document.getElementById('global-loader-bg');
	if (loader) {
		console.log('Loader найден и будет скрыт (onload)');
		loader.style.opacity = '0';
		setTimeout(function () {
			loader.style.display = 'none';
		}, 300);
	} else {
		console.log('Loader не найден!');
	}
}); 