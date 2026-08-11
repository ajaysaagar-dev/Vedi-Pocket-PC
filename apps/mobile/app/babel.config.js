const path = require('path');

/**
 * Resolve babel-preset-expo, falling back to the nested copy that ships
 * inside `expo/node_modules` in SDK 50+. This means the file works whether
 * or not `babel-preset-expo` is installed as a top-level devDependency.
 */
let expoPreset;
try {
  expoPreset = require('babel-preset-expo');
} catch {
  const expoDir = path.dirname(require.resolve('expo/package.json'));
  expoPreset = require(path.join(expoDir, 'node_modules/babel-preset-expo'));
}

module.exports = function (api) {
  api.cache(true);
  return {
    presets: [expoPreset],
    plugins: [
      // Required by Reanimated 4.x for gesture worklets (trackpad, animated
      // styles, shared values). Without this, Gesture.Pan / Gesture.Tap on
      // the trackpad silently fail to recognize touches and no events are
      // ever sent to the WS server.
      'react-native-worklets/plugin',
    ],
  };
};
