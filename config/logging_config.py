config = {
    "log_file": "release.log",
    "log_format": "{time} {level} {extra[name]}.{extra[function]} {extra[filename]}:{extra[line]} {message}",
    "log_level": "INFO",
    "log_rotation": "500 MB",
    "log_retention": "10 days",
    "log_compression": "zip"
}
