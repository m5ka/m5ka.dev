function refreshNowplaying(textElement, iconElement, username) {
  const endpoint = `https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=${username}&limit=1&api_key=8593a81dd2f1069b64528adcd184e9b2&format=json`
  fetch(endpoint).then(function(res) {
    return res.json();
  }).then(function(body) {
    const track = body.recenttracks.track[0];
    const playing = (track["@attr"] && track["@attr"].nowplaying) ? true : false;
    textElement.innerHTML = (playing ? "listening to " : "last listened to ") + track.name.toLowerCase();
    iconElement.classList.toggle("icon--spinning", playing);
  }).catch(function(err) {
    textElement.innerHTML = "couldn't grab current song"
    iconElement.classList.remove("icon--spinning");
  });
}

function setupNowplaying(textElement, iconElement, refreshInterval = 30000) {
  const username = textElement.dataset.lastfmUsername;
  if (!username) {
    throw "LastFM username not provided";
  }
  const doRefresh = () => refreshNowplaying(textElement, iconElement, username);
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
