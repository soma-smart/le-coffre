{{/*
Expand the name of the chart.
*/}}
{{- define "le-coffre.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "le-coffre.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Frontend fullname
*/}}
{{- define "le-coffre.frontend.fullname" -}}
{{- printf "%s-frontend" (include "le-coffre.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Backend fullname
*/}}
{{- define "le-coffre.backend.fullname" -}}
{{- printf "%s-backend" (include "le-coffre.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "le-coffre.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "le-coffre.labels" -}}
helm.sh/chart: {{ include "le-coffre.chart" . }}
{{ include "le-coffre.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "le-coffre.selectorLabels" -}}
app.kubernetes.io/name: {{ include "le-coffre.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "le-coffre.frontend.labels" -}}
{{ include "le-coffre.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "le-coffre.frontend.selectorLabels" -}}
{{ include "le-coffre.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Backend labels
*/}}
{{- define "le-coffre.backend.labels" -}}
{{ include "le-coffre.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "le-coffre.backend.selectorLabels" -}}
{{ include "le-coffre.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "le-coffre.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "le-coffre.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Resolve the name of the Kubernetes secret that holds JWT_SECRET_KEY.
- If config.jwt.secretKey is set, Helm manages the secret (named after the release).
- Otherwise, config.jwt.existingSecretName must point to a pre-existing secret.
*/}}
{{- define "le-coffre.jwtSecretName" -}}
{{- if .Values.config.jwt.secretKey -}}
{{- include "le-coffre.fullname" . -}}
{{- else -}}
{{- required "config.jwt.existingSecretName is required when config.jwt.secretKey is not set. Create the secret first: kubectl create secret generic <name> --from-literal=JWT_SECRET_KEY=\"$(openssl rand -base64 32)\" -n <namespace>" .Values.config.jwt.existingSecretName -}}
{{- end -}}
{{- end }}
