function getNowplayingCopy(textElement) {
  return {
    "listening": textElement.dataset.trListening ?? "listening to",
    "listened": textElement.dataset.trListened ?? "last listened to",
    "error": textElement.dataset.trError ?? "couldn't grab current song"
  }
}

function refreshNowplaying(textElement, iconElement, username, copy) {
  const endpoint = `https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=${username}&limit=1&api_key=8593a81dd2f1069b64528adcd184e9b2&format=json`
  fetch(endpoint).then(function(res) {
    return res.json();
  }).then(function(body) {
    const track = body.recenttracks.track[0];
    const playing = !!(track["@attr"] && track["@attr"].nowplaying);
    const currentStatus = playing ? copy.listening : copy.listened;
    textElement.innerHTML = `${currentStatus} ${track.name.toLowerCase()}`;
    iconElement.classList.toggle("icon--spinning", playing);
  }).catch(function(err) {
    textElement.innerHTML = copy.error;
    iconElement.classList.remove("icon--spinning");
  });
}

function setupNowplaying(textElement, iconElement, refreshInterval = 30000) {
  const username = textElement.dataset.lastfmUsername;
  if (!username) {
    throw "LastFM username not provided";
  }
  const copy = getNowplayingCopy(textElement);
  const doRefresh = () => refreshNowplaying(textElement, iconElement, username, copy);
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
