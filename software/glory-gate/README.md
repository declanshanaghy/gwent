# Glory Gate - Gwent Companion Web Interface

Glory Gate is the React-based web interface for the Gwent Companion system. Named after one of the six gates in Novigrad (connecting Farcorners district to Glory Lane), this application provides a digital interface for managing and interacting with the Gwent Companion device.

## Overview

Glory Gate connects to the Gwent Companion device via a REST API and WebSocket interface, allowing players to:

- View game state and scores in real-time
- Manage player decks and cards
- Access game history and statistics
- Configure device settings
- Monitor system status

## Architecture

- **Frontend**: React Single Page Application
- **State Management**: React Context API and hooks
- **API Communication**: Axios for REST API calls, Socket.io for WebSocket communication
- **UI Components**: Custom components styled with CSS modules
- **Routing**: React Router for navigation

## Connection to Gwent Companion

Glory Gate connects to the Gwent Companion device's REST API and WebSocket server, which are exposed by the `gwent` service running on the Raspberry Pi. The connection details are configured in the application settings.

## Available Scripts

In the project directory, you can run:

### `yarn start`

Runs the app in the development mode.<br />
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.<br />
You will also see any lint errors in the console.

### `yarn test`

Launches the test runner in the interactive watch mode.<br />
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `yarn build`

Builds the app for production to the `build` folder.<br />
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.<br />
Your app is ready to be deployed!

## Deployment

To deploy the Glory Gate application to the Gwent Companion device:

1. Build the application with `yarn build`
2. Copy the build files to the Raspberry Pi:
   ```
   scp -r build/ user@raspberry-pi-ip:/path/to/web/directory
   ```
3. Configure the Raspberry Pi's web server to serve the application

## Integration with Gwent Companion

Glory Gate integrates with the Gwent Companion device through:

1. **REST API**: For configuration, deck management, and game history
2. **WebSocket**: For real-time updates of game state and scores

The API endpoints and WebSocket events are documented in the [API Documentation](../docs/api.md).

## Development

When developing Glory Gate, you can run the application locally and connect to either:

1. A physical Gwent Companion device on your network
2. A local development instance of the `gwent` service

To connect to a local development instance, set the `REACT_APP_API_URL` environment variable:

```
REACT_APP_API_URL=http://localhost:5000 yarn start
```

## Project Structure

- `src/components/`: React components
- `src/contexts/`: React context providers
- `src/hooks/`: Custom React hooks
- `src/api/`: API and WebSocket communication
- `src/utils/`: Utility functions
- `src/pages/`: Page components
- `src/styles/`: Global styles and themes

## License

MIT
