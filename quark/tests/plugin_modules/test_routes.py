# Copyright 2013 Openstack Foundation
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
#  under the License.

import contextlib

import mock
from neutron.common import exceptions

from quark.db import api as db_api
from quark import exceptions as quark_exceptions
from quark.tests import test_quark_plugin


class TestQuarkGetRoutes(test_quark_plugin.TestQuarkPlugin):
    @contextlib.contextmanager
    def _stubs(self, routes):
        with mock.patch("quark.db.api.route_find") as route_find:
            route_find.return_value = routes
            yield

    def test_get_routes(self):
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=2)
        with self._stubs(routes=[route]):
            res = self.plugin.get_routes(self.context)
            for key in route.keys():
                self.assertEqual(res[0][key], route[key])

    def test_get_route(self):
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=2)
        with self._stubs(routes=route):
            res = self.plugin.get_route(self.context, 1)
            for key in route.keys():
                self.assertEqual(res[key], route[key])

    def test_get_route_not_found_fails(self):
        with self._stubs(routes=None):
            with self.assertRaises(quark_exceptions.RouteNotFound):
                self.plugin.get_route(self.context, 1)


class TestQuarkCreateRoutes(test_quark_plugin.TestQuarkPlugin):
    @contextlib.contextmanager
    def _stubs(self, create_route, find_routes, subnet):
        db_mod = "quark.db.api"
        with contextlib.nested(
            mock.patch("%s.route_create" % db_mod),
            mock.patch("%s.route_find" % db_mod),
            mock.patch("%s.subnet_find" % db_mod)
        ) as (route_create, route_find, subnet_find):
            route_create.return_value = create_route
            route_find.return_value = find_routes
            subnet_find.return_value = subnet
            yield

    def test_create_route(self):
        subnet = dict(id=2)
        create_route = dict(id=1, cidr="172.16.0.0/24", gateway="172.16.0.1",
                            subnet_id=subnet["id"])
        route = dict(id=1, cidr="0.0.0.0/0", gateway="192.168.0.1",
                     subnet_id=subnet["id"])
        with self._stubs(create_route=create_route, find_routes=[route],
                         subnet=subnet):
            res = self.plugin.create_route(self.context,
                                           dict(route=create_route))
            for key in create_route.keys():
                self.assertEqual(res[key], create_route[key])

    def test_create_route_no_subnet_fails(self):
        subnet = dict(id=2)
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=subnet["id"])
        with self._stubs(create_route=route, find_routes=[], subnet=None):
            with self.assertRaises(exceptions.SubnetNotFound):
                self.plugin.create_route(self.context, dict(route=route))

    def test_create_no_other_routes(self):
        subnet = dict(id=2)
        create_route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                            subnet_id=subnet["id"])
        with self._stubs(create_route=create_route, find_routes=[],
                         subnet=subnet):
            res = self.plugin.create_route(self.context,
                                           dict(route=create_route))
            self.assertEqual(res["cidr"], create_route["cidr"])

    def test_create_conflicting_route_raises(self):
        subnet = dict(id=2)
        create_route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                            subnet_id=subnet["id"])
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=subnet["id"])
        with self._stubs(create_route=create_route, find_routes=[route],
                         subnet=subnet):
            with self.assertRaises(quark_exceptions.RouteConflict):
                self.plugin.create_route(self.context,
                                         dict(route=create_route))


class TestQuarkDeleteRoutes(test_quark_plugin.TestQuarkPlugin):
    @contextlib.contextmanager
    def _stubs(self, route):
        db_mod = "quark.db.api"
        with contextlib.nested(
            mock.patch("%s.route_delete" % db_mod),
            mock.patch("%s.route_find" % db_mod),
        ) as (route_delete, route_find):
            route_find.return_value = route
            yield route_delete, route_find

    def test_delete_route(self):
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=2)
        with self._stubs(route=route) as (route_delete, route_find):
            self.plugin.delete_route(self.context, 1)
            self.assertTrue(route_delete.called)

    def test_delete_route_not_found_fails(self):
        with self._stubs(route=None):
            with self.assertRaises(quark_exceptions.RouteNotFound):
                self.plugin.delete_route(self.context, 1)

    def test_delete_route_deletes_correct_route(self):
        route = dict(id=1, cidr="192.168.0.0/24", gateway="192.168.0.1",
                     subnet_id=2)
        with self._stubs(route=route) as (route_delete, route_find):
            self.plugin.delete_route(self.context, 1)
            self.assertTrue(route_find.called_with(context=self.context, id=1,
                                                   scope=db_api.ONE))
            self.assertTrue(route_delete.called)
