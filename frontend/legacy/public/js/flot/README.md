# Flot

`jquery.flot.js` is the unmodified `dist/es5/jquery.flot.js` bundle of the npm package
[`flot` 4.2.6](https://www.npmjs.com/package/flot/v/4.2.6) (MIT, see `LICENSE.txt`).
npm integrity:
`sha512-Iz4HCet1ZBQnjGwECz4jseD1zMnh7m2XJIMI6A62l8h2SeceLYOEmYGNQto1XhkSM9fUmqzyKhWwJ+RolWLydg==`.

The bundle already contains the time axis, hover and legend plugins.  The resize plugin is
not used: `listenerstat.js` redraws through a `ResizeObserver` instead of the plugin's
250 ms polling.

Used only by Analytics → Listener Stats (`js/airtime/listenerstat/listenerstat.js`).
It replaced Flot 0.8.3 (2014) on 2026-11-11.
