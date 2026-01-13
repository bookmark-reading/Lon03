# Lon03

### Install and start the Python websocket server
1. Start Python virtual machine
    ```
    cd python-server
    python3 -m venv .venv
    ```
    Mac
    ```
    source .venv/bin/activate
    ```
    Windows
    ```
    .venv\Scripts\activate
    ```

2. Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set environment variables:
    
    The AWS access key and secret are required for the Python application, as they are needed by the underlying Smithy authentication library.
    ```bash
    export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET"
    export AWS_DEFAULT_REGION="us-east-1"
    ```
    The WebSocket host and port are optional. If not specified, the application will default to `localhost` and port `8081`.
    ```bash
    export HOST="localhost"
    export WS_PORT=8081
    ```
    The health check port is optional for container deployment such as ECS/EKS. If the environment variable below is not specified, the service will not start the HTTP endpoint for health checks.
    ```bash
    export HEALTH_PORT=8082 
    ```
    
4. Start the python websocket server
    ```bash
    python server.py
    ```

> Keep the Python WebSocket server running, then run the section below to launch the React web application, which will connect to the WebSocket service.

### Install and start the REACT frontend application
1. Navigate to the `react-client` folder
    ```bash
    cd react-client
    ```
2. Install
    ```bash
    npm install
    ```

3. This step is optional: set environment variables for the React app. If not provided, the application defaults to `ws://localhost:8081`.

    ```bash
    export REACT_APP_WEBSOCKET_URL='YOUR_WEB_SOCKET_URL'
    ```

4. If you want to run the React code outside the workshop environment, update the `homepage` value in the `react-client/package.json` file from "/proxy/3000/" to "."

5. Run
    ```
    npm start
    ```

When using Chrome, if there’s no sound, please ensure the sound setting is set to Allow, as shown below.
![chrome-sound](./static/chrome-sound-setting.png)

⚠️ **Warning:** Known issue: This UI is intended for demonstration purposes and may encounter state management issues after frequent conversation start/stop actions. Refreshing the page can help resolve the issue.