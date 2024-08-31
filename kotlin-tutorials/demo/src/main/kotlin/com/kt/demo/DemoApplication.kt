package com.kt.demo

data class Foo<T>(val value: T)

class Bar<T>(val value: T)

fun <T> display(value: T) {
    println(value)
}

fun <T> createContainer(value: T): Container<T> = Container(value)

interface Event

interface PipelineProducer<T : Event> {
    fun send(topic: String, value: T)
}

data class RegistrationEvent(val name: String): Event

class RegistrationEventPipelineProducer : PipelineProducer<RegistrationEvent> {
    override fun send(topic: String, value: RegistrationEvent) {
        println("Sending event $value to topic $topic")
    }
}

class AnyPipelineProducer : PipelineProducer<Any> {
    override fun send(topic: String, value: Any) {
        val event = value as RegistrationEvent

        println("Sending event $value to topic $topic")
    }
}

data class Container<T>(val value: T)

fun main(args: Array<String>) {
    display("hello")
    display(123)
    display(Foo("world"))

    Container("hello")
    Container(123)

    createContainer("world")
}
