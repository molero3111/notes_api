import { combineReducers } from 'redux';
import authReducer from './AuthReducer'; // authentication reducer

const rootReducer = combineReducers({
  auth: authReducer,
});

export default rootReducer;
