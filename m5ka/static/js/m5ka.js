function getNowplayingCopy(textElement) {
  return {
    "listening": textElement.dataset.trListening ?? "listening to",
    "listened": textElement.dataset.trListened ?? "last listened to",
    "error": textElement.dataset.trError ?? "couldn't grab current song"
  }
}

function refreshNowplaying(textElement, iconElement, endpoint, copy) {
  fetch(endpoint).then(function(res) {
    if (!res.ok) {
      throw new Error(`Now playing request failed with ${res.status}`);
    }
    return res.json();
  }).then(function(body) {
    const currentStatus = body.playing ? copy.listening : copy.listened;
    textElement.textContent = `${currentStatus} ${body.track.toLowerCase()}`;
    iconElement.classList.toggle("icon--spinning", body.playing);
  }).catch(function(err) {
    textElement.textContent = copy.error;
    iconElement.classList.remove("icon--spinning");
  });
}

// The server caches Last.fm for a minute, so polling faster gains nothing.
function setupNowplaying(textElement, iconElement, refreshInterval = 60000) {
  const endpoint = textElement.dataset.endpoint;
  if (!endpoint) {
    throw "Now playing endpoint not provided";
  }
  const copy = getNowplayingCopy(textElement);
  const doRefresh = () => refreshNowplaying(textElement, iconElement, endpoint, copy);
  setInterval(doRefresh, refreshInterval);
  doRefresh();
}

document.addEventListener("DOMContentLoaded", function() {
  const nowplaying = document.querySelector("#nowlistening");
  if (nowplaying) {
    const nowplayingIcon = document.querySelector("#nowlisteningicon");
    setupNowplaying(nowplaying, nowplayingIcon);
  }
});
