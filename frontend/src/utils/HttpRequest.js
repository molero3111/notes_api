import axios from 'axios';

const axiosInstance = axios.create({
    baseURL: 'http://127.0.0.1:8000/api'
});


export async function sendRequest(method, url, data = {}, authenticate = true) {
    try {
        let token = null;
        let headers = {
            // 'Accept': 'application/json' // Add Accept header
        };
        if (authenticate) {
            token = localStorage.getItem('token');
            if (!token) {
                return false;
            }
            headers.Authorization = `Token ${token}`;
        }
        const response = await axiosInstance.request({
            method,
            url,
            data,
            headers
        });
        return response.data;
    } catch (error) {
        console.error('Error with request:', error);
        throw error;
    }
}
