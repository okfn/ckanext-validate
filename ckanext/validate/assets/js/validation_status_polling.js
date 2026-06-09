(function () {
  "use strict";

  var POLL_INTERVAL_MS = 3000;
  var MAX_ATTEMPTS = 40;

  var STATE_CLASSES = [
    "validate-badge--valid",
    "validate-badge--invalid",
    "validate-badge--error",
    "validate-badge--pending",
    "validate-badge--running"
  ];

  var STATE_TO_CLASS = {
    success: "validate-badge--valid",
    failure: "validate-badge--invalid",
    error: "validate-badge--error",
    pending: "validate-badge--pending",
    running: "validate-badge--running",
    not_validated: "validate-badge--pending"
  };

  function isActiveState(state) {
    return state === "pending" || state === "running";
  }

  function getLabel(badge, state) {
    var key = "label" + state
      .replace(/_([a-z])/g, function (_, letter) {
        return letter.toUpperCase();
      })
      .replace(/^([a-z])/, function (_, letter) {
        return letter.toUpperCase();
      });

    return badge.dataset[key] || state;
  }

  function setBadgeState(badge, state) {
    var label = getLabel(badge, state);

    STATE_CLASSES.forEach(function (className) {
      badge.classList.remove(className);
    });

    badge.classList.add(STATE_TO_CLASS[state] || "validate-badge--pending");
    badge.dataset.validationState = state;

    if (isActiveState(state)) {
      badge.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + label;
    } else {
      badge.textContent = label;
    }
  }

  function updateAllBadgesForResource(resourceId, state) {
    var badges = document.querySelectorAll(
      '.js-validation-status[data-resource-id="' + resourceId + '"]'
    );

    badges.forEach(function (badge) {
      setBadgeState(badge, state);
    });
  }

  function buildStatusUrl(badge) {
    var url = badge.dataset.validationUrl;
    var resourceId = badge.dataset.resourceId;

    if (!url || !resourceId) {
      return null;
    }

    var separator = url.indexOf("?") === -1 ? "?" : "&";
    return url + separator + "id=" + encodeURIComponent(resourceId);
  }

  function pollBadge(badge) {
    var resourceId = badge.dataset.resourceId;
    var statusUrl = buildStatusUrl(badge);
    var attempts = 0;

    if (!resourceId || !statusUrl) {
      return;
    }

    function poll() {
      attempts += 1;

      fetch(statusUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json"
        }
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Validation status request failed");
          }
          return response.json();
        })
        .then(function (payload) {
          if (!payload || !payload.success || !payload.result) {
            return;
          }

          var state = payload.result.state || "not_validated";
          updateAllBadgesForResource(resourceId, state);

          if (isActiveState(state) && attempts < MAX_ATTEMPTS) {
            window.setTimeout(poll, POLL_INTERVAL_MS);
          }
        })
        .catch(function () {
          if (attempts < MAX_ATTEMPTS) {
            window.setTimeout(poll, POLL_INTERVAL_MS);
          }
        });
    }

    poll();
  }

  function initValidationStatusPolling() {
    var badges = document.querySelectorAll(".js-validation-status");
    var alreadyPolling = {};

    badges.forEach(function (badge) {
      var state = badge.dataset.validationState;
      var resourceId = badge.dataset.resourceId;

      if (!resourceId || alreadyPolling[resourceId]) {
        return;
      }

      if (isActiveState(state)) {
        alreadyPolling[resourceId] = true;
        pollBadge(badge);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", initValidationStatusPolling);
})();
