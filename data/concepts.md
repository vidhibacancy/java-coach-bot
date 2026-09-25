# Java & Spring Boot Concepts

## Java Basics

Java is a high-level, class-based, object-oriented, platform-independent
programming language. Source code (.java files) is compiled by javac into
bytecode (.class files), which the Java Virtual Machine (JVM) then
interprets or JIT-compiles into native machine code at runtime. This
"compile once, run anywhere" model is what makes Java portable across
operating systems, since only the JVM needs to be platform-specific, not
the compiled bytecode.

Java is statically typed, meaning variable types are checked at compile
time rather than runtime. Primitive types (int, long, double, boolean,
char, byte, short, float) are stored directly by value, while everything
else is an object, stored by reference. Every Java class implicitly
extends Object, which provides default implementations of methods like
equals(), hashCode(), and toString() that are commonly overridden.

## Object-Oriented Programming

Java is built around four core OOP principles. Encapsulation bundles data
(fields) and behavior (methods) together in a class, hiding internal state
behind private fields and exposing controlled access through public
methods (getters/setters), so internal representation can change without
breaking external callers. Inheritance lets a class (subclass) reuse and
extend the fields and methods of another class (superclass) via `extends`,
enabling code reuse and polymorphic behavior. Polymorphism allows a
reference of a supertype to point to a subtype object, and the correct
overridden method is chosen at runtime based on the object's actual type
(dynamic dispatch) — this is how a `List<Animal>` can hold both `Dog` and
`Cat` objects and correctly call each one's overridden `makeSound()`.
Abstraction hides implementation complexity behind a simpler interface,
achieved in Java through abstract classes and interfaces.

Constructors initialize a new object's state and share the class's name
with no return type. If no constructor is defined, Java provides a
no-argument default constructor automatically — but only if no other
constructor is explicitly defined. Method overloading lets a class have
multiple methods with the same name but different parameter lists,
resolved at compile time; method overriding lets a subclass replace a
superclass method's behavior, resolved at runtime.

## Collections Framework

The Java Collections Framework provides a unified architecture for storing
and manipulating groups of objects. The three main interfaces are List
(ordered, allows duplicates — ArrayList, LinkedList), Set (no duplicates —
HashSet, TreeSet, LinkedHashSet), and Map (key-value pairs — HashMap,
TreeMap, LinkedHashMap; Map is not technically a Collection but is part of
the framework).

ArrayList is backed by a resizable array, giving O(1) indexed access but
O(n) insertion/removal in the middle. LinkedList is a doubly-linked list,
giving O(1) insertion/removal at a known position but O(n) random access.
HashMap offers average O(1) get/put by hashing keys into buckets; since
Java 8, a bucket whose linked list of colliding entries grows past a
threshold (8) converts to a red-black tree, improving worst-case lookup
from O(n) to O(log n). TreeMap keeps keys in sorted order (via a red-black
tree internally) at the cost of O(log n) operations instead of HashMap's
average O(1). LinkedHashMap preserves insertion order while still offering
near-HashMap performance.

Iterating and modifying a collection at the same time (outside the
iterator's own remove() method) throws a ConcurrentModificationException
for most standard collections, because they track a modification count
that the iterator checks on each step ("fail-fast" behavior).

## Multithreading & Concurrency

A Java program can run multiple threads concurrently, sharing the same
heap memory but each with its own stack. Creating a thread is done either
by extending Thread and overriding run(), or (preferred) by implementing
Runnable and passing it to a Thread, which keeps your class free to extend
something else and separates "the task" from "the mechanism that runs it."

The `synchronized` keyword provides mutual exclusion around a block or
method, ensuring only one thread executes it at a time for a given lock
object, at the cost of blocking other threads until it's released.
`ReentrantLock` offers the same mutual exclusion with more control: timed
or interruptible lock attempts, fairness policies, and multiple condition
variables — but it must be released manually in a finally block, unlike
synchronized which releases automatically even on an exception.

`volatile` guarantees visibility of a variable's latest value across
threads (reads/writes go to main memory, not a per-thread cache) and
prevents certain instruction reordering, but does not make compound
operations like increment (i++) atomic. For atomic compound operations
without full locking, classes like AtomicInteger or AtomicReference use
compare-and-swap (CAS) operations at the hardware level.

`ExecutorService` manages a reusable pool of worker threads for running
submitted tasks (Runnable/Callable), avoiding the overhead and risk of
creating a raw Thread per task. A deadlock occurs when two or more threads
each hold a lock the other is waiting for; it's avoided by acquiring locks
in a consistent order, using timed lock attempts, or minimizing the number
of locks held simultaneously.

## Exception Handling

Java exceptions are objects representing an abnormal condition, thrown
with `throw` and caught with try/catch. Checked exceptions (subclasses of
Exception other than RuntimeException, like IOException) must be either
caught or declared with `throws` — the compiler enforces handling them,
since they typically represent recoverable external conditions. Unchecked
exceptions (subclasses of RuntimeException, like NullPointerException or
IllegalArgumentException) aren't checked at compile time and usually
represent programming bugs.

A `finally` block always executes after a try/catch, whether or not an
exception occurred, and is commonly used for cleanup. `try-with-resources`
automatically closes any resource implementing AutoCloseable when the try
block exits — normally or via exception — which is safer and less verbose
than manual close() calls in a finally block, and correctly attaches any
exception from close() as a suppressed exception on the original one
rather than silently discarding it.

Custom exceptions are created by extending Exception (checked) or
RuntimeException (unchecked), letting an application define domain-specific
error types (like `InsufficientFundsException`) that carry more meaningful
information than a generic exception would.

## Java 8+ Features

Lambda expressions provide a concise way to implement a functional
interface's single abstract method inline, e.g. `(a, b) -> a + b`, removing
the boilerplate of an anonymous inner class. A functional interface has
exactly one abstract method (optionally annotated @FunctionalInterface),
and the `java.util.function` package provides common ones: Function<T,R>,
Predicate<T>, Supplier<T>, and Consumer<T>.

The Stream API enables functional-style processing of collections:
`list.stream().filter(...).map(...).collect(Collectors.toList())` reads as
a declarative pipeline rather than an imperative loop. map() transforms
each element 1-to-1; flatMap() transforms each element into its own stream
and flattens all of them into one, useful for flattening nested
collections. Streams are lazy — intermediate operations like filter/map
don't execute until a terminal operation (collect, forEach, reduce) is
invoked.

Optional<T> makes the possibility of "no value" explicit in a method's
return type, avoiding null checks scattered through calling code — used
mainly as a return type, not as a field or parameter type. Default methods
on interfaces (`default void foo() {...}`) let an interface provide a
concrete implementation, enabling API evolution without breaking existing
implementing classes.

## var and Local Variable Type Inference (Java 10)

`var`, introduced in Java 10, lets the compiler infer a local variable's
type from its initializer, e.g. `var list = new ArrayList<String>();`
instead of `ArrayList<String> list = new ArrayList<>();`. Java remains
statically typed — `var` doesn't make it dynamically typed like
JavaScript's `var` — the type is fixed at compile time from the
initializer and can never change afterward. It's restricted to local
variables with an initializer (not fields, method parameters, or return
types), and is best used when the type is already obvious from the
right-hand side, to cut redundancy without hurting readability.

## Switch Expressions (Java 14)

Switch expressions, finalized in Java 14, let a `switch` produce a value
directly using arrow syntax (`case X -> value`), removing the need for
fall-through `break` statements and the bugs they cause:
```
int numDays = switch (month) {
    case FEBRUARY -> 28;
    case APRIL, JUNE, SEPTEMBER, NOVEMBER -> 30;
    default -> 31;
};
```
Multiple case labels can be combined on one line, and `yield` returns a
computed value from inside a block-bodied case. Unlike traditional switch
statements, switch expressions must be exhaustive (cover every possible
case, or include a `default`), which the compiler enforces at compile time.

## Text Blocks (Java 15)

Text blocks, finalized in Java 15, let you write multi-line string
literals without escaping every newline and quote, using triple-quote
delimiters:
```
String json = """
    {
      "name": "Java",
      "version": 21
    }
    """;
```
The compiler strips a common leading whitespace (based on the
least-indented line), so the text block's indentation in your source code
doesn't leak into the actual string value — making embedded JSON, SQL, or
HTML far more readable than building the same string with `+` and `\n`.

## Records (Java 16)

A record is a compact, purpose-built class for modeling immutable data,
previewed in Java 14 and finalized in Java 16. Declaring
`record Point(int x, int y) {}` automatically generates a canonical
constructor, private final fields, public accessor methods (`x()`, `y()`
— no "get" prefix), plus `equals()`, `hashCode()`, and `toString()` based
on all the record's components, eliminating the boilerplate normally
needed for a simple immutable data carrier (a POJO/DTO). A record can
still declare extra methods, static fields, and a compact constructor
(for validating arguments without repeating the full parameter list), but
its fields are always final, and it cannot extend another class (though
it can implement interfaces), since it implicitly extends
`java.lang.Record`.

## Pattern Matching: instanceof and switch (Java 16 & 21)

Pattern matching for `instanceof`, finalized in Java 16, folds a type
check and a cast into one expression: `if (obj instanceof String s) { ... }`
binds `s` as a `String` directly inside the `if`, removing the old
two-step "check, then cast" boilerplate. Pattern matching for `switch`,
finalized in Java 21, extends this to switch statements/expressions,
matching on type patterns directly:
```
String describe(Object obj) {
    return switch (obj) {
        case Integer i -> "an int: " + i;
        case String s -> "a string of length " + s.length();
        case null -> "it's null";
        default -> "something else";
    };
}
```
Combined with records, Java 21 also added record patterns, letting a case
label destructure a record's components directly:
`case Point(int x, int y) -> ...`.

## Sealed Classes and Interfaces (Java 17)

Sealed classes/interfaces, finalized in Java 17, restrict which other
classes or interfaces may extend or implement them, using the `sealed`
modifier with a `permits` clause:
`public sealed interface Shape permits Circle, Square, Triangle {}`. Every
permitted subtype must itself be declared `final`, `sealed`, or
`non-sealed`. This closes the set of possible subtypes at compile time,
which pairs especially well with pattern matching in a switch expression:
the compiler can verify every case is covered (exhaustiveness) without
needing a `default` branch, turning a missed case into a compile error
instead of a runtime surprise.

## Virtual Threads (Java 21)

Virtual threads, finalized in Java 21 under Project Loom, are lightweight
threads managed by the JVM rather than mapped one-to-one onto OS threads.
A traditional (platform) thread is relatively expensive — megabytes of
stack space, OS-level scheduling — but the JVM can multiplex millions of
cheap virtual threads onto a small pool of OS "carrier" threads,
automatically unmounting a virtual thread from its carrier whenever it
blocks on I/O. This lets the simple, easy-to-read "one thread per
request" style of code scale to very high concurrency without rewriting
everything in a complex asynchronous/reactive style just to avoid
exhausting OS threads. Existing blocking code (like a JDBC call) works
unmodified on a virtual thread, since blocking now only ties up a cheap
virtual thread rather than a scarce OS thread.

## Sequenced Collections (Java 21)

Java 21 introduced the `SequencedCollection`, `SequencedSet`, and
`SequencedMap` interfaces, giving any collection with a defined encounter
order (like `List`, `LinkedHashSet`, `LinkedHashMap`) a uniform way to
access its first and last elements and to obtain a reversed view —
`getFirst()`, `getLast()`, `addFirst()`, `addLast()`, and `reversed()` —
without needing collection-specific tricks, like `list.get(list.size() - 1)`
for the last element or wrapping a list just to iterate it backwards. This
retrofits one consistent API across previously inconsistent ordered
collection types.

## Java Version Timeline (LTS releases)

Since Java 8 (well before which releases were infrequent and monolithic),
Java has shipped a new feature release every six months, with a
Long-Term Support (LTS) release periodically — most production systems
track the LTS releases rather than every six-month release. Java 8 (2014,
LTS) introduced lambdas, the Stream API, and Optional. Java 11 (2018, LTS)
added the `var` keyword for local variables (backported from Java 10), a
new HTTP Client API, and removed several deprecated modules. Java 17
(2021, LTS) finalized sealed classes, pattern matching for `instanceof`,
and records. Java 21 (2023, LTS) finalized virtual threads, pattern
matching for `switch` (including record patterns), and sequenced
collections. Knowing which LTS release a feature landed in matters in
interviews, since many companies stay on an LTS version for years and
skip non-LTS releases entirely.

## JVM & Memory Management

The JVM's heap stores all objects and is shared across threads, divided
into a Young generation (Eden + two Survivor spaces) and an Old generation,
based on the observation that most objects die young. Minor garbage
collections run frequently on the Young generation using a fast copying
algorithm; objects that survive several minor GCs get promoted to the Old
generation, which is collected less often via a slower major/full GC.
Metaspace (replacing PermGen since Java 8) stores class metadata, growing
into native memory rather than the heap.

Each thread has its own Stack, storing method call frames and local
variables — exhausting it (e.g. via unbounded recursion) throws a
StackOverflowError, while exhausting heap space throws an
OutOfMemoryError. Reference types beyond normal strong references include
soft references (collected only under memory pressure, useful for caches),
weak references (collected as soon as no strong references remain, used by
WeakHashMap), and phantom references (used to schedule cleanup actions
after an object is finalized, without allowing access to it).

## Spring Core: IoC and Dependency Injection

Spring's core idea is Inversion of Control (IoC): instead of a class
creating its own dependencies, the Spring container creates and injects
them, decoupling components from how their dependencies are constructed.
Dependency Injection (DI) is the mechanism — via constructor injection
(preferred, since it makes dependencies explicit, immutable, and fails
fast at startup if something's missing), field injection (@Autowired on a
field directly, simpler but harder to test and hides required
dependencies), or setter injection (for optional dependencies).

A Spring "bean" is any object managed by the IoC container. Beans are
declared via stereotype annotations (@Component, @Service, @Repository,
@Controller) which are discovered through component scanning, or via
explicit @Bean methods in a @Configuration class. @Service marks business
logic; @Repository additionally enables automatic translation of
database-specific exceptions into Spring's DataAccessException hierarchy.

A bean's lifecycle runs through instantiation, dependency population,
Aware-interface callbacks, BeanPostProcessor pre-initialization,
@PostConstruct/afterPropertiesSet(), then the bean is ready for use, and
finally @PreDestroy/destroy() runs during application shutdown.

## Spring Boot Fundamentals

Spring Boot builds on the Spring Framework to eliminate most manual
configuration through auto-configuration and "starter" dependencies. The
`@SpringBootApplication` annotation combines `@Configuration` (marks a
source of bean definitions), `@EnableAutoConfiguration` (lets Spring Boot
guess and configure beans based on what's on the classpath — e.g.
auto-configuring a DataSource if a JDBC driver is present), and
`@ComponentScan` (scans the package and sub-packages for components).

Spring profiles let you define environment-specific beans/configuration
(dev, test, prod) and activate the right one via
`spring.profiles.active`, so environment-specific settings — like a
different datasource for local development versus production — don't
require code changes. `application.properties` or `application.yml` holds
externalized configuration, and profile-specific variants
(`application-prod.yml`) override the base file's values when that profile
is active.

Spring Boot Actuator exposes production-ready endpoints (health, metrics,
info) for monitoring a running application without writing that
infrastructure yourself.

## Spring Data JPA

Spring Data JPA reduces boilerplate for database access by letting you
define a repository interface (extending JpaRepository<Entity, IdType>)
and get CRUD methods, paging, and sorting for free, plus custom query
methods derived from method names (like `findByEmailAndActiveTrue`)
without writing any implementation.

Entities are mapped to database tables via `@Entity` and `@Table`, with
`@Id` marking the primary key. Relationships use `@OneToMany`,
`@ManyToOne`, `@ManyToMany`, and `@OneToOne`, each configurable with a
FetchType of LAZY (load related data only when accessed — the safer
default) or EAGER (load immediately with the parent, which can cause
unnecessary queries or memory use).

The N+1 query problem occurs when fetching N parent entities triggers 1
query for the parents plus N further queries — one per parent — to lazily
load a related collection. It's fixed with `JOIN FETCH` in a JPQL query,
`@EntityGraph` for a specific query, or batch-fetching configuration.
`@Transactional` wraps a method's database operations in a single
transaction, so they all commit or all roll back together.

## Spring Security Basics

Spring Security provides authentication (verifying who a user is) and
authorization (deciding what they're allowed to do) for a Spring
application. A `SecurityFilterChain` defines a chain of servlet filters
that every request passes through — for authentication, session handling,
CSRF protection, and more — before reaching your controller.

For stateless REST APIs, session-based authentication is usually replaced
with token-based authentication (commonly JWT — JSON Web Tokens): the
client authenticates once, receives a signed token containing claims about
the user, and sends it in the Authorization header on subsequent requests;
the server verifies the token's signature rather than looking up a session
store. Method-level security annotations like `@PreAuthorize("hasRole('ADMIN')")`
let you restrict individual methods based on the authenticated user's
roles or permissions.

## Building REST APIs with Spring Boot

A REST controller (`@RestController`) maps HTTP requests to handler
methods via `@GetMapping`, `@PostMapping`, `@PutMapping`, and
`@DeleteMapping`. Path variables (`@PathVariable`) capture parts of the
URL; request parameters (`@RequestParam`) capture query string values;
`@RequestBody` deserializes the request body (typically JSON) into a Java
object.

An operation is idempotent if performing it multiple times produces the
same result as performing it once. GET, PUT, and DELETE are expected to be
idempotent; POST typically is not, since each call is expected to create a
new resource — this matters because clients may retry a request after a
network failure, and a non-idempotent retried POST could create duplicate
resources.

`@ControllerAdvice` combined with `@ExceptionHandler` methods centralizes
exception handling across all controllers, mapping specific exception
types to consistent HTTP responses (e.g. a 404 with a structured error
body for a NotFoundException) instead of duplicating try/catch logic in
every controller.

## Microservices Concepts

A microservices architecture splits an application into independently
deployable services, each owning its own data and logic, trading the
simplicity of a monolith for independent scaling, deployment, and
technology choice — at the cost of added operational and networking
complexity. An API Gateway sits in front of these services as a single
entry point, routing requests, handling cross-cutting concerns like auth
and rate limiting, and avoiding the need for clients to know every
service's location individually.

Service discovery lets services find each other's current network location
dynamically (via a registry like Eureka or Consul) rather than hardcoded
addresses, since instances can scale up/down or move at any time. The
Circuit Breaker pattern prevents a service from repeatedly calling a
failing downstream dependency — after enough failures, the circuit "opens"
and fails fast, periodically allowing a trial request through to check if
the dependency has recovered.

The CAP theorem states a distributed data store can guarantee only two of
Consistency, Availability, and Partition tolerance at once; since network
partitions are unavoidable in practice, a real distributed system is
really choosing between consistency and availability whenever a partition
occurs.
