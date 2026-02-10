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
Backend image name
*/}}
{{- define "le-coffre.backend.image" -}}
{{- $tag := .Values.backend.image.tag | default .Chart.AppVersion -}}
{{- if .Values.backend.image.registry }}
{{- printf "%s/%s:%s" .Values.backend.image.registry .Values.backend.image.repository $tag -}}
{{- else }}
{{- printf "%s:%s" .Values.backend.image.repository $tag -}}
{{- end }}
{{- end }}

{{/*
Frontend image name
*/}}
{{- define "le-coffre.frontend.image" -}}
{{- $tag := .Values.frontend.image.tag | default .Chart.AppVersion -}}
{{- if .Values.frontend.image.registry }}
{{- printf "%s/%s:%s" .Values.frontend.image.registry .Values.frontend.image.repository $tag -}}
{{- else }}
{{- printf "%s:%s" .Values.frontend.image.repository $tag -}}
{{- end }}
{{- end }}

{{/*
Database URL helper
*/}}
{{- define "le-coffre.databaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql://{{ .Values.postgresql.auth.username }}:{{ .Values.postgresql.auth.password }}@{{ include "le-coffre.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{ .Values.backend.config.databaseUrl }}
{{- end -}}
{{- end }}
