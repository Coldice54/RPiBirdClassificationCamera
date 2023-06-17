import React, { useEffect, useState, useRef, useCallback } from 'react';
import { PaperProvider, TextInput } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';
import { AppRegistry, Platform, Linking, Alert, Share, Pressable, Button, SafeAreaView, ActivityIndicator, FlatList, Text, View, Image, StyleSheet, TouchableOpacity } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import _ from "lodash"
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import AsyncStorage from '@react-native-async-storage/async-storage';


const styles = StyleSheet.create({
	container: {
		paddingTop: 0,
		flex: 1,
	},
	tableHeader: {
		flexDirection: "row",
		justifyContent: "space-evenly",
		alignItems: "center",
		paddingLeft: 4,
		backgroundColor: "#37C2D0",
		height: 50
	},
	tableRow: {
		paddingLeft: 4,
		flexDirection: "row",
		//height: "20vh",
		fontSize: 12,
		alignItems: "center",
		textAlign: "center",
	},
	columnHeader: {
		width: "33%",
		// justifyContent: "left",
		//alignItems: "center"
	},
	columnHeaderTxt: {
		fontSize: 12,
		color: "white",
		fontWeight: "bold",
	},
	columnRowTxt: {
		width: "33%",
		fontSize: 12,
	},
	detailsText: {
        fontSize: 18,
        fontWeight: "bold",
        height: 40,
    },
});
let cameraIP = '192.168.1.61'; //will be in settings later
let cameraPort = '5000';
function getFullCameraIP() { return 'http://' + cameraIP + ':' + cameraPort; }

Notifications.setNotificationHandler({
	handleNotification: async () => ({
		shouldShowAlert: true,
		shouldPlaySound: false,
		shouldSetBadge: false,
	}),
});

const sendPushTokenToCamera = async (token) => {
    //use a post request to save the settings
    let tokenRoute = getFullCameraIP() + '/pushToken';
    const response = await fetch(tokenRoute, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pushToken: token
      })
    });
  };

async function registerForPushNotificationsAsync() {
	let token;


	if (Platform.OS === 'android') {
		await Notifications.setNotificationChannelAsync('default', {
			name: 'default',
			importance: Notifications.AndroidImportance.MAX,
			vibrationPattern: [0, 250, 250, 250],
			lightColor: '#FF231F7C',
		});
	}


	if (Device.isDevice) {
		const { status: existingStatus } = await Notifications.getPermissionsAsync();
		let finalStatus = existingStatus;
		if (existingStatus !== 'granted') {
			const { status } = await Notifications.requestPermissionsAsync();
			finalStatus = status;
		}
		if (finalStatus !== 'granted') {
			console.error("token failed");
			return;
		}
		token = (await Notifications.getExpoPushTokenAsync()).data;
		console.warn("my token:" + token);
	} else {
		alert('Must use physical device for Push Notifications');
	}
	//alert('token: ' + token);
	return token;
}

const columnNameToKey = {
	"Timestamp": "dateTime",
	"Identification": "birdIdentification",
	"Image": "birdImage"
}

function MainPage({ navigation }) {
	//Table to display and allow sorting of visits
	const sortTable = (column) => {
		const newDirection = direction === "desc" ? "asc" : "desc"
		const sortedData = _.orderBy(birdVisits, columnNameToKey[column], [newDirection])
		setSelectedColumn(column)
		setDirection(newDirection)
		setBirdVisits(sortedData)
	}

	const tableHeader = () => (
		<View style={styles.tableHeader}>
			{
				columns.map((column, index) => {
					{
						return (
							<TouchableOpacity
								key={index}
								style={styles.columnHeader}
								onPress={() => sortTable(column)}>
								<Text style={styles.columnHeaderTxt}>{column + " "}
									{selectedColumn === column && <MaterialCommunityIcons
										name={direction === "desc" ? "arrow-down-drop-circle" : "arrow-up-drop-circle"}
									/>
									}
								</Text>
							</TouchableOpacity>
						)
					}
				})
			}
		</View>
	)
	const [columns, setColumns] = useState([
		"Timestamp",
		"Identification",
		"Image"
	])
	const [direction, setDirection] = useState(null)
	const [selectedColumn, setSelectedColumn] = useState(null)
	const [isLoading, setLoading] = useState(true);



	const [birdVisits, setBirdVisits] = useState([])
	const getBirdVisits = async () => {
		try {
			cameraIP = await AsyncStorage.getItem('cameraIP');
			cameraPort = await AsyncStorage.getItem('cameraPort');
		} catch (e) {
			console.log(e)
		}

		try {
			let visitsRoute = getFullCameraIP() + '/visitsjson';
			const response = await fetch(visitsRoute);
			const json = await response.json();
			setBirdVisits(json);
			console.log(json)
		} catch (error) {
			console.error(error);
		} finally {
			setLoading(false);
			console.log()
		}
	};

	const [expoPushToken, setExpoPushToken] = useState('');
	const [notification, setNotification] = useState(false);
	const notificationListener = useRef();
	const responseListener = useRef();

	useEffect(() => {
		getBirdVisits();
		registerForPushNotificationsAsync().then(token => {
			setExpoPushToken(token);
			sendPushTokenToCamera(token);
		});	
		notificationListener.current = Notifications.addNotificationReceivedListener(notification => {
			setNotification(notification);
		});


		responseListener.current = Notifications.addNotificationResponseReceivedListener(response => {
			console.log(response);
		});


		return () => {
			Notifications.removeNotificationSubscription(notificationListener.current);
			Notifications.removeNotificationSubscription(responseListener.current);
		};
	}, []);

	return (
		<View style={styles.container}>
			<FlatList
				data={birdVisits}
				style={{ width: "100%" }}
				keyExtractor={(item, index) => index + ""}
				ListHeaderComponent={tableHeader}
				stickyHeaderIndices={[0]}
				renderItem={({ item, index }) => {
					//const { imageUri } = getFullCameraIP() + '/static/birdcaptures/' + item.birdImage;
					return (
						<View style={{ ...styles.tableRow, backgroundColor: index % 2 == 1 ? "#F0FBFC" : "white" }}>

							<Text style={styles.columnRowTxt}>{item.dateTime}</Text>

							<Text style={styles.columnRowTxt}>{item.birdIdentification}</Text>
							<Pressable
								onPress={() =>
									navigation.navigate('Details', { item })
								}>
								<Image source={{ uri: getFullCameraIP() + '/static/birdcaptures/' + item.birdImage }} style={{ width: 150, height: 100, resizeMode: 'contain' }} />
							</Pressable>
						</View>
					)
				}}
			/>
			<StatusBar style="auto" />
		</View>
	)
}




function DetailsPage({ route }) {
	const OpenURLButton = ({ url, children }) => {
		const handlePress = useCallback(async () => {
			// Checking if the link is supported for links with custom URL scheme.
			const supported = await Linking.canOpenURL(url);

			if (supported) {
				// Opening the link with some app, if the URL scheme is "http" the web link should be opened
				// by some browser in the mobile
				await Linking.openURL(url);
			} else {
				Alert.alert(`Don't know how to open this URL: ${url}`);
			}
		}, [url]);

		return <Button title={children} onPress={handlePress} />;
	};
	const { item } = route.params;
	console.log(item.birdImage)
	const shareMsg = "Check out this " + item.birdIdentification + " I captured on my bird monitor!"
	const onShare = async () => {
		try {
			const result = await Share.share({
				message:
					shareMsg
			});
			if (result.action === Share.sharedAction) {
				if (result.activityType) {
					// shared with activity type of result.activityType
				} else {
					// shared
				}
			} else if (result.action === Share.dismissedAction) {
				// dismissed
			}
		} catch (error) {
			Alert.alert(error.message);
		}
	};
	return (
		<View style={{ flex: 1, alignItems: 'center' }}>
            <Image source={{uri: getFullCameraIP() + '/static/birdcaptures/' + item.birdImage}} style={{ width: 360, height: 240 }} />
            <Text style={styles.detailsText}> {item.birdIdentification}</Text>
            <Text style={styles.detailsText}>{item.dateTime}</Text>
            <Text style={styles.detailsText}>Confidence:  0.{item.identificationConfidence}</Text>
            <Button onPress={onShare} title="Share" />
			<OpenURLButton url={getFullCameraIP() + '/static/birdcaptures/' + item.birdImage}>Image Link</OpenURLButton>
        </View>
	);
}
const Stack = createStackNavigator();

function MainStackPage() {
	return (
		<Stack.Navigator>
			<Stack.Screen name="Visits" component={MainPage} options={{ headerShown: false, }} />
			<Stack.Screen name="Details" component={DetailsPage} />
			<Stack.Screen name="Settings" component={SettingsPage} />
		</Stack.Navigator>
	);
}

function SettingsPage() {
	const [deviceSettings, setDeviceSettings] = React.useState({ threshold: 0.5 });
	const [deviceSettingsLoading, setDeviceSettingsLoading] = React.useState(true);
	const [ip, onChangeIP] = React.useState('');
	const [port, onChangePort] = React.useState('');
	const fetchDeviceSettings = async () => {
		try {
			let testMode = false;
			let json = null;
			if (testMode) {
				json = { threshold: 0.5 }
			} else {
				let settingsRoute = getFullCameraIP() + '/settings';
				const response = await fetch(settingsRoute);
				json = await response.json();
			}
			if (json !== null) {
				setDeviceSettings(json);
			}
			setDeviceSettingsLoading(false);
			console.log(json)
		} catch (error) {
			console.error(error);
		} finally {
		}
	};
	const sendDeviceSettings = async () => {
		//use a post request to save the settings
		let settingsRoute = getFullCameraIP() + '/settings';
		console.log("sending device settings", deviceSettings);
		const response = await fetch(settingsRoute, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(deviceSettings)
		});
	};
	useEffect(() => {
		fetchDeviceSettings();
	}, []);
	return (
		<>
			<SafeAreaView style={{ paddingTop: '20%' }}>
				<TextInput
					style={styles.input}
					placeholder="xxx.xxx.xx.xx"
					defaultValue={cameraIP}
					onChangeText={(val => {
						cameraIP = val;
						AsyncStorage.setItem('cameraIP', val)
					})}
					label="IP"
					keyboardType="numeric"
				/>
				<TextInput
					style={styles.input}
					placeholder="xxxx"
					defaultValue={cameraPort}
					onChangeText={(val => {
						cameraPort = val;
						AsyncStorage.setItem('cameraPort', val)
					})}
					label="Port"
					keyboardType="numeric"
				/>
				{!deviceSettingsLoading &&
					<TextInput style={styles.input}
						defaultValue={deviceSettings["threshold"].toString()}
						onChangeText={(val => {
							deviceSettings["threshold"] = parseFloat(val);
						})}
						onBlur={sendDeviceSettings}
						label="Threshold"
						keyboardType="numeric"
					/>
				}
				{!deviceSettingsLoading &&
					<TextInput style={styles.input}
						defaultValue={deviceSettings["frameCount"].toString()}
						onChangeText={(val => {
							deviceSettings["frameCount"] = parseInt(val);
						})}
						onBlur={sendDeviceSettings}
						label="# Frames to Select Best Confidence From"
						keyboardType="numeric"
					/>
				}
			</SafeAreaView>
		</>
	);

}

const Tab = createBottomTabNavigator();

export default function App() {
	//Main
	return (
		<PaperProvider>
			<NavigationContainer>
				<Tab.Navigator>
					<Tab.Screen name="Visits"
						component={MainStackPage}
						options={{
							tabBarIcon: ({ color, size }) => (
								<MaterialCommunityIcons name="bird" color={color} size={size} />
							),
						}}
					/>
					<Tab.Screen name="Settings"
						component={SettingsPage}
						options={{
							tabBarIcon: ({ color, size }) => (
								<MaterialCommunityIcons name="cog" color={color} size={size} />
							),
						}}
					/>
				</Tab.Navigator>
			</NavigationContainer>
		</PaperProvider>
	);
};

