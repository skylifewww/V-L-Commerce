(function() {
    'use strict';
    
    function initHeroProductBlock() {
        // Используем делегирование событий для динамических элементов
        document.addEventListener('change', function(e) {
            // Проверяем, что это селектор выбора продукта
            if (e.target.matches('select[data-chooser-url*="snippet"]')) {
                var select = e.target;
                var productId = select.value;
                
                if (!productId) return;
                
                // Ищем родительский блок с полями
                var fieldWrapper = select.closest('.field-content');
                if (!fieldWrapper) return;
                
                // Ищем родительский блок StreamField
                var streamBlock = select.closest('[data-streamfield-block]');
                if (!streamBlock) return;
                
                // Загружаем данные продукта через AJAX
                fetch('/api/product/' + productId + '/')
                    .then(response => response.json())
                    .then(data => {
                        // Находим поля в этом же блоке
                        var titleField = streamBlock.querySelector('input[name*="title"]');
                        var priceField = streamBlock.querySelector('input[name*="price"]');
                        var oldPriceField = streamBlock.querySelector('input[name*="old_price"]');
                        var subtitleField = streamBlock.querySelector('textarea[name*="subtitle"]');
                        
                        // Заполняем поля если они пустые
                        if (titleField && !titleField.value && data.name) {
                            titleField.value = data.name;
                            // Триггерим событие изменения
                            titleField.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        if (priceField && !priceField.value && data.price) {
                            priceField.value = data.price;
                            priceField.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        if (oldPriceField && !oldPriceField.value && data.old_price) {
                            oldPriceField.value = data.old_price;
                            oldPriceField.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        if (subtitleField && !subtitleField.value && data.description) {
                            var truncatedDesc = data.description.length > 200 
                                ? data.description.substring(0, 200) + '...' 
                                : data.description;
                            subtitleField.value = truncatedDesc;
                            subtitleField.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    })
                    .catch(error => console.error('Error loading product:', error));
            }
        });
    }
    
    // Инициализация при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHeroProductBlock);
    } else {
        initHeroProductBlock();
    }
    
    // Для динамически добавляемых блоков в StreamField
    if (typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    initHeroProductBlock();
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
})();
