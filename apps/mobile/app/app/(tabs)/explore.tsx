// This file intentionally left minimal - not used by PC Remote
import { View, Text, StyleSheet } from 'react-native';

export default function ExploreScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>PC Remote</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#07070F',
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    color: '#F8FAFC',
    fontSize: 18,
  },
});
