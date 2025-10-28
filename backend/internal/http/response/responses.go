package response

import (
	"encoding/json"
	"net/http"
	"plexwatcher/internal/types"
)

func WriteSuccess(writer http.ResponseWriter, msg string, data any, code int) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(code)
	resp := types.ResponseSuccess{
		Code:    code,
		Message: msg,
		Data:    data,
	}
	json.NewEncoder(writer).Encode(resp)
}

func WriteError(writer http.ResponseWriter, msg string, code int) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(code)
	resp := types.ResponseError{
		Code:    code,
		Message: msg,
	}
	json.NewEncoder(writer).Encode(resp)
}
