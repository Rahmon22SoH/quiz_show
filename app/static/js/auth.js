// Удаляем или комментируем отладочный вывод
// console.log('User info:', userInfo);

// Вместо этого можно использовать более безопасный подход
if (DEBUG_MODE) {
    // Выводим только в режиме отладки и только минимальную информацию
    console.log('User authenticated:', userInfo.authenticated);
} 