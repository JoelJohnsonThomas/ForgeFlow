{{/*
Standard label set applied to every resource. Single source of truth so a
chart-rename only touches this file.
*/}}
{{- define "forgeflow.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: forgeflow
{{- end -}}

{{/*
Per-component selector labels. Pass the component name (api, mcp,
dashboard, postgres, migrate) as the first argument.
*/}}
{{- define "forgeflow.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/*
Compute the Secret name. Honors `secrets.existingSecret` if set so
external secret stores (sealed-secrets, eso) can own the lifecycle.
*/}}
{{- define "forgeflow.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{ .Values.secrets.existingSecret }}
{{- else -}}
{{ printf "%s-secrets" .Release.Name }}
{{- end -}}
{{- end -}}

{{- define "forgeflow.configName" -}}
{{ printf "%s-config" .Release.Name }}
{{- end -}}

{{- define "forgeflow.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Per-component image. Combines registry, component, and tag.
Usage: include "forgeflow.image" (dict "Values" .Values "component" "api")
*/}}
{{- define "forgeflow.image" -}}
{{ printf "%s/%s:%s" .Values.image.registry .component .Values.image.tag }}
{{- end -}}
