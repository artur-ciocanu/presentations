rootProject.name = "demo"
include("src:main:java")
findProject(":src:main:java")?.name = "java"
