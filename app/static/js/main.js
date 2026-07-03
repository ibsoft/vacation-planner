document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });

    document.querySelectorAll('table').forEach(function(table) {
        if (table.querySelectorAll('th').length > 0) {
            var searchInput = document.createElement('input');
            searchInput.className = 'form-control form-control-sm mb-3';
            searchInput.type = 'search';
            searchInput.placeholder = 'Search...';
            searchInput.style.maxWidth = '300px';

            var wrapper = table.closest('.table-responsive');
            if (wrapper) {
                wrapper.parentNode.insertBefore(searchInput, wrapper);
            }

            searchInput.addEventListener('keyup', function() {
                var filter = this.value.toLowerCase();
                var rows = table.querySelectorAll('tbody tr');
                rows.forEach(function(row) {
                    var text = row.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                });
            });
        }
    });

    var notifMenu = document.getElementById('notifMenu');
    if (notifMenu) {
        notifMenu.addEventListener('click', function(e) {
            var item = e.target.closest('[data-notif-id]');
            if (item) {
                var notifId = item.getAttribute('data-notif-id');
                var li = item.closest('li');
                var token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
                fetch('/notifications/' + notifId + '/read', { method: 'POST', headers: { 'X-CSRFToken': token } }).then(function() {
                    li.style.transition = 'opacity 0.3s';
                    li.style.opacity = '0';
                    setTimeout(function() {
                        li.remove();
                        var remaining = notifMenu.querySelectorAll('[data-notif-id]').length;
                        var badge = document.querySelector('#notifDropdown .badge');
                        if (remaining === 0) {
                            notifMenu.innerHTML = '';
                            var noNotif = document.createElement('li');
                            noNotif.innerHTML = '<span class="dropdown-item-text text-muted small">' + notifMenu.getAttribute('data-empty-text') + '</span>';
                            notifMenu.appendChild(noNotif);
                            if (badge) badge.remove();
                        } else if (badge) {
                            var count = parseInt(badge.textContent);
                            if (count > 1) badge.textContent = count - 1;
                            else badge.remove();
                        }
                    }, 300);
                });
            }
        });
    }

    document.addEventListener('click', function(e) {
        var btn = e.target.closest('[data-confirm]');
        if (btn) {
            e.preventDefault();
            var message = btn.getAttribute('data-confirm');
            var form = btn.closest('form');
            confirmModal(message, function() {
                if (form) {
                    form.submit();
                }
            });
        }
    });
});

function showSpinner(text) {
    var overlay = document.getElementById('spinnerOverlay');
    if (text) {
        document.getElementById('spinnerText').textContent = text;
    }
    overlay.classList.remove('d-none');
    overlay.style.display = 'flex';
}

function hideSpinner() {
    var overlay = document.getElementById('spinnerOverlay');
    overlay.classList.add('d-none');
    overlay.style.display = 'none';
}

function confirmModal(message, onConfirm) {
    var modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('confirmModalBody').textContent = message;
    var btn = document.getElementById('confirmModalBtn');
    var newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
    newBtn.addEventListener('click', function() {
        modal.hide();
        if (onConfirm) onConfirm();
    });
    modal.show();
}
