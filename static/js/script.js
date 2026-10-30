/* =====================================================
   SPENDSENSE - PASSWORD MATCH VALIDATION
   ===================================================== */

document.addEventListener("DOMContentLoaded", function () {

    const newPassword =
        document.getElementById("new_password");

    const confirmPassword =
        document.getElementById("confirm_password");

    const feedback =
        document.getElementById("password-feedback");


    // Only run this code on pages
    // that contain the password fields
    if (
        !newPassword ||
        !confirmPassword ||
        !feedback
    ) {
        return;
    }


    function checkPasswordMatch() {

        const password =
            newPassword.value;

        const confirm =
            confirmPassword.value;


        // Nothing entered in confirm password
        if (confirm === "") {

            confirmPassword.classList.remove(
                "password-match-error",
                "password-match-success"
            );

            feedback.textContent = "";

            feedback.classList.remove(
                "error",
                "success"
            );

            return;
        }


        // Passwords match
        if (password === confirm) {

            confirmPassword.classList.remove(
                "password-match-error"
            );

            confirmPassword.classList.add(
                "password-match-success"
            );

            feedback.textContent =
                "✓ Passwords match";

            feedback.classList.remove("error");

            feedback.classList.add("success");

        }


        // Passwords don't match
        else {

            confirmPassword.classList.remove(
                "password-match-success"
            );

            confirmPassword.classList.add(
                "password-match-error"
            );

            feedback.textContent =
                "✕ Passwords do not match";

            feedback.classList.remove("success");

            feedback.classList.add("error");

        }

    }


    // Check while typing
    newPassword.addEventListener(
        "input",
        checkPasswordMatch
    );

    confirmPassword.addEventListener(
        "input",
        checkPasswordMatch
    );

});
// =====================================================
// ADD TRANSACTION - CATEGORY FILTER
// =====================================================

document.addEventListener("DOMContentLoaded", function () {

    const transactionType =
        document.getElementById("type");

    const categorySelect =
        document.getElementById("category_id");

    if (!transactionType || !categorySelect) {
        return;
    }

    const allCategories = Array.from(
        categorySelect.querySelectorAll(
            "option[data-type]"
        )
    );

    function filterCategories() {

        const selectedType =
            transactionType.value;

        // Reset category
        categorySelect.value = "";

        allCategories.forEach(function (option) {

            if (option.dataset.type === selectedType) {

                option.style.display = "";

            } else {

                option.style.display = "none";

            }

        });
    }

    transactionType.addEventListener(
        "change",
        filterCategories
    );

});
// =====================================================
// DELETE TRANSACTION
// =====================================================

function deleteTransaction(transactionId) {

    const confirmed = confirm(
        "Are you sure you want to delete this transaction?"
    );

    if (!confirmed) {
        return;
    }

    const form = document.createElement("form");

    form.method = "POST";

    form.action =
        "/delete-transaction/" + transactionId;

    document.body.appendChild(form);

    form.submit();

}
document.addEventListener("DOMContentLoaded", function () {

    const typeSelect = document.getElementById("type");
    const categorySelect = document.getElementById("category_id");

    if (!typeSelect || !categorySelect) {
        return;
    }

    const allCategories = Array.from(
        categorySelect.options
    ).map(option => ({
        value: option.value,
        text: option.text,
        type: option.dataset.type
    }));

    function updateCategories() {

        const selectedType = typeSelect.value;
        const currentCategory = categorySelect.value;

        categorySelect.innerHTML = "";

        allCategories
            .filter(category => category.type === selectedType)
            .forEach(category => {

                const option = document.createElement("option");

                option.value = category.value;
                option.textContent = category.text;
                option.dataset.type = category.type;

                if (category.value === currentCategory) {
                    option.selected = true;
                }

                categorySelect.appendChild(option);

            });
    }

    typeSelect.addEventListener(
        "change",
        updateCategories
    );

    updateCategories();

});
/* =========================================================
   TRANSACTION SEARCH AND TYPE FILTER
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const searchInput =
        document.getElementById("transactionSearch");

    const typeFilter =
        document.getElementById("transactionTypeFilter");

    const rows =
        document.querySelectorAll(".transactions-table tbody tr");

    const monthGroups =
        document.querySelectorAll(".transaction-month-group");

    if (!searchInput || !typeFilter || !rows.length) {
        return;
    }

    function filterTransactions() {

        const searchText =
            searchInput.value.toLowerCase().trim();

        const selectedType =
            typeFilter.value;

        // Filter individual transaction rows
        rows.forEach(function (row) {

            const rowText =
                row.textContent.toLowerCase();

            const typeCell =
                row.querySelector(".transaction-badge");

            const transactionType =
                typeCell
                    ? typeCell.textContent.toLowerCase().trim()
                    : "";

            const matchesSearch =
                rowText.includes(searchText);

            const matchesType =
                selectedType === "all" ||
                transactionType === selectedType;

            row.style.display =
                matchesSearch && matchesType
                    ? ""
                    : "none";

        });

        // Hide month groups that have no visible transactions
        monthGroups.forEach(function (group) {

            const groupRows =
                group.querySelectorAll(".transactions-table tbody tr");

            const hasVisibleRows =
                Array.from(groupRows).some(function (row) {
                    return row.style.display !== "none";
                });

            group.style.display =
                hasVisibleRows ? "" : "none";

        });

    }

    searchInput.addEventListener(
        "input",
        filterTransactions
    );

    typeFilter.addEventListener(
        "change",
        filterTransactions
    );

});
/* =========================================================
   PROFILE DROPDOWN
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const profileButton = document.getElementById("profileButton");
    const profileMenu = document.getElementById("profileMenu");

    if (!profileButton || !profileMenu) {
        return;
    }

    profileButton.addEventListener("click", function (event) {

        event.stopPropagation();

        profileMenu.classList.toggle("show");

    });


    document.addEventListener("click", function (event) {

        if (
            !profileMenu.contains(event.target) &&
            !profileButton.contains(event.target)
        ) {
            profileMenu.classList.remove("show");
        }

    });

});