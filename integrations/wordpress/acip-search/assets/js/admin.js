/**
 * ACIP admin settings page behaviour: "Bulk import now" and "Test connection".
 * Localized data (ajaxUrl, nonce, labels) is provided via `acipAdmin`
 * (see ACIP_Admin::enqueue_assets in includes/class-acip-admin.php).
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof acipAdmin === "undefined") return;

    var bulkBtn = document.getElementById("acip-bulk");
    var bulkOut = document.getElementById("acip-bulk-result");
    if (bulkBtn && bulkOut) {
      bulkBtn.addEventListener("click", function () {
        bulkOut.textContent = acipAdmin.i18n.working;
        var body = new URLSearchParams({
          action: "acip_bulk_import",
          nonce: acipAdmin.nonce,
        });
        fetch(acipAdmin.ajaxUrl, { method: "POST", body: body })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            bulkOut.textContent = j.success
              ? acipAdmin.i18n.imported.replace("%d", j.data.count)
              : acipAdmin.i18n.failed;
          })
          .catch(function () {
            bulkOut.textContent = acipAdmin.i18n.failed;
          });
      });
    }

    var testBtn = document.getElementById("acip-test");
    var testOut = document.getElementById("acip-test-result");
    if (testBtn && testOut) {
      testBtn.addEventListener("click", function () {
        testOut.textContent = acipAdmin.i18n.working;
        var body = new URLSearchParams({
          action: "acip_test_connection",
          nonce: testBtn.getAttribute("data-nonce"),
          api_url: document.getElementById("acip-api-url").value,
          widget_key: document.getElementById("acip-widget-key").value,
          sync_key: document.getElementById("acip-sync-key").value,
        });
        fetch(acipAdmin.ajaxUrl, { method: "POST", body: body })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            testOut.textContent = j.success ? j.data.message : (j.data && j.data.message) || acipAdmin.i18n.failed;
          })
          .catch(function () {
            testOut.textContent = acipAdmin.i18n.failed;
          });
      });
    }
  });
})();
