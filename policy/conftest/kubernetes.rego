package main

required_labels := {"app", "env", "owner"}

required_resources := [
	["requests", "cpu"],
	["requests", "memory"],
	["limits", "cpu"],
	["limits", "memory"],
]

deny[msg] {
	input.kind == "Rollout"
	container := input.spec.template.spec.containers[_]
	endswith(container.image, ":latest")
	msg := sprintf("Rollout %q: container %q usa a tag :latest", [input.metadata.name, container.name])
}

deny[msg] {
	input.kind == "Rollout"
	container := input.spec.template.spec.containers[_]
	container.securityContext.privileged == true
	msg := sprintf("Rollout %q: container %q está privileged", [input.metadata.name, container.name])
}

deny[msg] {
	input.kind == "Rollout"
	label := required_labels[_]
	not input.metadata.labels[label]
	msg := sprintf("Rollout %q: label obrigatória %q ausente", [input.metadata.name, label])
}

deny[msg] {
	input.kind == "Rollout"
	container := input.spec.template.spec.containers[_]
	resource := required_resources[_]
	not container.resources[resource[0]][resource[1]]
	msg := sprintf(
		"Rollout %q: container %q sem resources.%s.%s",
		[input.metadata.name, container.name, resource[0], resource[1]],
	)
}
