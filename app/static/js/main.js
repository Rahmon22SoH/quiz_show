// Обновление времени
function updateTime() {
    var currentTime = moment().format('LLL');
    document.getElementById('current-time').textContent = currentTime;
}
// Плавное закрытие меню
function initNavigation() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');

    // Обработка клика по гамбургеру
    navbarToggler.addEventListener('click', function() {
        navbarCollapse.classList.contains('show') 
            ? closeMenu() 
            : openMenu();
    });

    // Закрытие меню при клике по ссылке
    document.querySelectorAll('.nav-btn').forEach(link => {
        link.addEventListener('click', () => {
            if (navbarCollapse.classList.contains('show')) {
                closeMenu();
            }
        });
    });

    // Закрытие меню при клике вне его
    document.addEventListener('click', (event) => {
        const isClickInside = navbarCollapse.contains(event.target) || 
                            navbarToggler.contains(event.target);
        
        if (!isClickInside && navbarCollapse.classList.contains('show')) {
            closeMenu();
        }
    });

    function closeMenu() {
        navbarCollapse.classList.remove('show');
        navbarToggler.setAttribute('aria-expanded', 'false');
        navbarCollapse.classList.add('collapsing');
        setTimeout(() => {
            navbarCollapse.classList.remove('collapsing');
        }, 300);
    }

    function openMenu() {
        navbarCollapse.classList.add('show');
        navbarToggler.setAttribute('aria-expanded', 'true');
    }
}
// Закрытие меню при клике
function initNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            const navbarCollapse = document.getElementById('navbarNav');
            if (navbarCollapse.classList.contains('show')) {
                new bootstrap.Collapse(navbarCollapse).hide();
            }
        });
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    updateTime();
    setInterval(updateTime, 60000);
    initNavigation();
});