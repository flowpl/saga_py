
saga_py
=======

Create a series of dependent actions and roll everything back when one of them fails.


Install
-------

.. code-block:: bash

    $ pip install saga_py


Usage
-----


Simple example
^^^^^^^^^^^^^^

.. code-block:: python

    from saga import SagaBuilder

    counter1 = 0
    counter2 = 0

    def incr_counter1(amount):
        global counter1
        counter1 += amount

    def incr_counter2(amount):
        global counter2
        counter2 += amount

    def decr_counter1(amount):
        global counter1
        counter1 -= amount

    def decr_counter2(amount):
        global counter2
        counter2 -= amount

    SagaBuilder \
        .create() \
        .action(lambda: incr_counter1(15), lambda: decr_counter1(15)) \
        .action(lambda: incr_counter2(1), lambda: decr_counter2(1)) \
        .action() \
        .build() \
        .execute()

    # if every action succeeds, the effects of all actions are applied
    print(counter1)  # 15
    print(counter2)  # 1


An action fails example
^^^^^^^^^^^^^^^^^^^^^^^

If one action fails, the compensations for all already executed actions are run and a SagaError is raised that wraps
all Exceptions encountered during the run.

.. code-block:: python

    from saga import SagaBuilder, SagaError

    counter1 = 0
    counter2 = 0

    def incr_counter1(amount):
        global counter1
        counter1 += amount

    def incr_counter2(amount):
        global counter2
        counter2 += amount
        raise BaseException('some error happened')

    def decr_counter1(amount):
        global counter1
        counter1 -= amount

    def decr_counter2(amount):
        global counter2
        counter2 -= amount

    try:
        SagaBuilder \
            .create() \
            .action(lambda: incr_counter1(15), lambda: decr_counter1(15)) \
            .action(lambda: incr_counter2(1), lambda: decr_counter2(1)) \
            .action() \
            .build() \
            .execute()
    except SagaError as e:
        print(e)  # wraps the BaseException('some error happened')

    print(counter1)  # 0
    print(counter2)  # 0


An action and a compensation fail example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since the compensation for action2 fails, the compensation effect is undefined from the framework's perspective,
all other compensations are run regardless.

.. code-block:: python

    from saga import SagaBuilder, SagaError

    counter1 = 0
    counter2 = 0

    def incr_counter1(amount):
        global counter1
        counter1 += amount

    def incr_counter2(amount):
        global counter2
        counter2 += amount
        raise BaseException('some error happened')

    def decr_counter1(amount):
        global counter1
        counter1 -= amount

    def decr_counter2(amount):
        global counter2
        raise BaseException('compensation also fails')

    try:
        SagaBuilder \
            .create() \
            .action(lambda: incr_counter1(15), lambda: decr_counter1(15)) \
            .action(lambda: incr_counter2(1), lambda: decr_counter2(1)) \
            .action() \
            .build() \
            .execute()
    except SagaError as e:
        print(e)  #

    print(counter1)  # 0
    print(counter2)  # 1


Passing values from one action to the next
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An action can return a dict of return values.
The dict is then passed as keyword arguments to the next action and it's corresponding compensation.
No values can be passed between compensations.

.. code-block:: python

    from saga import SagaBuilder, SagaError

    counter1 = 0
    counter2 = 0

    def incr_counter1(amount):
        global counter1
        counter1 += amount
        return {'counter1_value': counter1}

    def incr_counter2(counter1_value):
        global counter2
        counter2 += amount

    def decr_counter1(amount):
        global counter1
        counter1 -= amount

    def decr_counter2(counter1_value):
        global counter2
        counter2 -= amount

    SagaBuilder \
        .create() \
        .action(lambda: incr_counter1(15), lambda: decr_counter1(15)) \
        .action(incr_counter2, decr_counter2) \
        .action() \
        .build() \
        .execute()

    print(counter1)  # 15
    print(counter2)  # 15
